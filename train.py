"""
train.py
--------
The full training loop, using the Reed-Solomon-protected encoding
pipeline: quantum key -> RSA wrap -> AES encrypt -> Reed-Solomon encode ->
redundant replicate -> GAN hide/discriminate/decode.

PERFORMANCE FIX (this version): Reed-Solomon encoding is a genuinely
expensive pure-Python operation. The previous version called it fresh for
EVERY sample in EVERY batch of EVERY epoch -- with 200 synthetic samples
per epoch, that's 200 RS-encode calls per epoch just for training data prep,
which is why a 3-epoch smoke test was taking minutes instead of seconds.

Fix: RS-encode a fixed POOL of secrets ONCE before training starts, then
sample from that pool each batch. This cuts RS-encoding calls from
(epochs x batches_per_epoch x batch_size) down to just (pool_size) --
typically a 100x+ reduction. This is standard practice, not a shortcut:
the network still sees a healthy variety of secrets each epoch (sampled
randomly from the pool with replacement), same as how most datasets work.

Run directly for a quick smoke test (synthetic data, no downloads,
runs on CPU in well under a minute):
    python train.py
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.models as tv_models

from config import CFG
from models import Encoder, Decoder, Discriminator
from dataset import get_dataloader
from quantum_key import generate_quantum_key_bytes
from crypto_utils import encrypt_image_array_protected

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==================== Perceptual (VGG) Loss (NEW) ====================
# WHY: plain pixel-wise MSE has a well-known failure mode -- when the
# network is uncertain about an unfamiliar texture (e.g. a dense pile of
# limes it barely saw in training), MSE rewards it for "hedging" toward
# an average color/texture rather than committing to a sharp, correct
# answer -- this is exactly the "green limes decoded as orange blobs"
# problem. A perceptual loss compares VGG feature-map activations instead
# of raw pixels, which is far more tolerant of small spatial shifts and
# pushes the network toward getting the STRUCTURE/content right rather
# than literally matching pixel colors -- the standard fix for this
# failure mode in image-generation literature.

_VGG_FEATURES = None
_IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
_IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def _get_vgg_features():
    """Loads a frozen VGG16 (up through relu3_3) ONCE and reuses it --
    downloads pretrained ImageNet weights on first use (needs internet;
    cached by torch afterwards, so this cost is paid only once ever)."""
    global _VGG_FEATURES
    if _VGG_FEATURES is None:
        weights = tv_models.VGG16_Weights.IMAGENET1K_V1
        vgg = tv_models.vgg16(weights=weights).features[:16].to(DEVICE)
        vgg.eval()
        for p in vgg.parameters():
            p.requires_grad = False
        _VGG_FEATURES = vgg
    return _VGG_FEATURES


def perceptual_loss(decoded: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """
    decoded, target: (B, 3, H, W) tensors in [-1, 1] (our usual convention).
    Rescales to [0, 1] then ImageNet-normalizes (what VGG expects), runs
    both through the frozen VGG feature extractor, and returns the MSE
    between their feature maps.
    """
    vgg = _get_vgg_features()
    mean = _IMAGENET_MEAN.to(decoded.device)
    std = _IMAGENET_STD.to(decoded.device)

    def _prep(x):
        x01 = (x.clamp(-1, 1) + 1) / 2
        return (x01 - mean) / std

    feat_decoded = vgg(_prep(decoded))
    feat_target = vgg(_prep(target))
    return nn.functional.mse_loss(feat_decoded, feat_target)


def tensor_to_uint8_array(tensor: torch.Tensor) -> np.ndarray:
    return ((tensor.clamp(-1, 1) + 1) * 127.5).byte().cpu().numpy()


def uint8_array_to_tensor(arr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(arr.astype(np.float32) / 127.5 - 1.0)


def encrypt_batch_secrets(secret_batch: torch.Tensor, key: bytes):
    """
    Encodes a batch of secrets through the full protected pipeline
    (downscale -> AES -> Reed-Solomon -> replicate) -- one call per secret.

    NOTE: this is for EVALUATION use (encoding a handful of test secrets
    after training), not for use inside the training loop -- during
    training, build_secret_cache() pre-encodes a pool once up front instead,
    since calling this per-batch was the cause of the earlier slowness bug.
    For evaluating just a few secrets, the per-call cost here is fine.

    Returns: (encoded_tensor, nonces, small_shape, protected_length, redundancy)
    -- same return shape as the old training-loop version, kept for
    compatibility with evaluate.py and the notebook.
    """
    encoded_tensors = []
    nonces = []
    small_shape = protected_length = redundancy = None

    for i in range(secret_batch.shape[0]):
        arr = tensor_to_uint8_array(secret_batch[i])
        full_encoded, nonce, small_shape, protected_length, redundancy = \
            encrypt_image_array_protected(
                arr, key, CFG.SECRET_DOWNSCALE_FACTOR,
                nsym=CFG.RS_NSYM, redundancy=CFG.RS_REDUNDANCY
            )
        encoded_tensors.append(uint8_array_to_tensor(full_encoded))
        nonces.append(nonce)

    return torch.stack(encoded_tensors), nonces, small_shape, protected_length, redundancy


def build_secret_cache(key: bytes, image_size: int, pool_size: int = 32,
                        use_synthetic: bool = True, folder_path: str = None):
    """
    THE performance fix. Generates `pool_size` unique secret images, and
    RS-encodes each ONE TIME ONLY -- this is the expensive step, done once
    up front instead of repeatedly inside the training loop.

    Returns a dict with parallel lists/tensors:
      secrets       -- (pool_size, 3, H, W) tensor, the true original secrets
      encoded       -- (pool_size, 3, H, W) tensor, ready to feed the encoder
      nonces        -- list of nonces, one per pooled secret
      small_shape, protected_length, redundancy -- same for the whole pool
      (all secrets use the same downscale factor / RS settings from CFG,
      so these metadata values are identical across the pool)
    """
    print(f"[cache] Pre-encoding a pool of {pool_size} secrets "
          f"(this is the one-time expensive step, not per-batch)...")

    if use_synthetic:
        raw_secrets = torch.rand(pool_size, 3, image_size, image_size) * 2 - 1
    else:
        from dataset import FolderSteganoDataset
        ds = FolderSteganoDataset(folder_path, image_size=image_size)
        idxs = np.random.choice(len(ds), size=min(pool_size, len(ds)), replace=False)
        raw_secrets = torch.stack([ds[i][1] for i in idxs])  # [1] = the "secret" half of each pair
        pool_size = raw_secrets.shape[0]

    encoded_list = []
    nonce_list = []
    small_shape = protected_length = redundancy = None

    for i in range(pool_size):
        arr = tensor_to_uint8_array(raw_secrets[i])
        full_encoded, nonce, small_shape, protected_length, redundancy = \
            encrypt_image_array_protected(
                arr, key, CFG.SECRET_DOWNSCALE_FACTOR,
                nsym=CFG.RS_NSYM, redundancy=CFG.RS_REDUNDANCY
            )
        encoded_list.append(uint8_array_to_tensor(full_encoded))
        nonce_list.append(nonce)
        if (i + 1) % 10 == 0 or (i + 1) == pool_size:
            print(f"[cache]   encoded {i + 1}/{pool_size}")

    print("[cache] Done. Training will now sample from this pool -- no more per-batch RS calls.")

    return {
        "secrets": raw_secrets,
        "encoded": torch.stack(encoded_list),
        "nonces": nonce_list,
        "small_shape": small_shape,
        "protected_length": protected_length,
        "redundancy": redundancy,
    }


def setup_security_layer():
    security = {}
    if CFG.USE_ENCRYPTION:
        security["aes_key"] = generate_quantum_key_bytes(CFG.AES_KEY_BYTES)
        print(f"[security] Quantum-assisted AES-{CFG.AES_KEY_BYTES*8} key generated: "
              f"{security['aes_key'].hex()}")
    else:
        security["aes_key"] = None

    if CFG.USE_ENCRYPTION and CFG.USE_KEY_EXCHANGE:
        from key_exchange import generate_receiver_keypair, wrap_aes_key
        priv, pub = generate_receiver_keypair(CFG.RSA_KEY_SIZE)
        security["receiver_private_key"] = priv
        security["receiver_public_key"] = pub
        security["wrapped_aes_key"] = wrap_aes_key(security["aes_key"], pub)
        print(f"[security] AES key wrapped with receiver's RSA-{CFG.RSA_KEY_SIZE} public key.")

    return security


def _save_checkpoint(encoder, decoder, discriminator, history, epoch=None,
                      checkpoint_name="qgan_stego_checkpoint.pt"):
    """
    Pulled out into its own function (CHANGED) so it can be called both
    mid-training and at the end -- a long CPU run (60 epochs on real
    images can take hours) is at real risk of being interrupted (laptop
    sleep, closed terminal, power cut), and previously the checkpoint was
    only written ONCE, after the very last epoch -- an interruption at
    epoch 55/60 would have thrown away all of it. Always writes to the
    SAME path, so the file is simply "the most recently completed epoch's
    weights", not a growing pile of per-epoch files.

    checkpoint_name (NEW): lets train() keep two SEPARATE checkpoints --
    one for the full encrypted+Reed-Solomon security pipeline, another
    for a plain (no-encryption) run trained purely for perceptual
    image-in-image hiding quality -- without one run overwriting the
    other.
    """
    os.makedirs(CFG.CHECKPOINT_DIR, exist_ok=True)
    ckpt_path = os.path.join(CFG.CHECKPOINT_DIR, checkpoint_name)
    torch.save({
        "encoder": encoder.state_dict(),
        "decoder": decoder.state_dict(),
        "discriminator": discriminator.state_dict(),
        "history": history,
        "last_completed_epoch": epoch,
    }, ckpt_path)
    if epoch is not None:
        print(f"[checkpoint] Progress saved after epoch {epoch} -> {ckpt_path}")
    else:
        print(f"[checkpoint] Saved model weights to {ckpt_path}")


def train(epochs=None, batch_size=None, image_size=None,
          use_synthetic=None, folder_path=None, use_encryption=None,
          alpha=None, beta=None, gamma=None, save_checkpoint=True,
          secret_pool_size=32, checkpoint_every=5, gamma_warmup_epochs=10,
          residual_strength=None, checkpoint_name=None,
          use_perceptual_loss=True, perceptual_weight=None,
          resume_from=None):
    epochs = CFG.EPOCHS if epochs is None else epochs
    batch_size = CFG.BATCH_SIZE if batch_size is None else batch_size
    image_size = CFG.IMAGE_SIZE if image_size is None else image_size
    use_synthetic = CFG.USE_SYNTHETIC_DATA if use_synthetic is None else use_synthetic
    folder_path = CFG.DATASET_FOLDER if folder_path is None else folder_path
    use_encryption = CFG.USE_ENCRYPTION if use_encryption is None else use_encryption
    alpha = CFG.ALPHA_RECONSTRUCTION if alpha is None else alpha
    beta = CFG.BETA_IMAGE_QUALITY if beta is None else beta
    gamma = CFG.GAMMA_ADVERSARIAL if gamma is None else gamma
    perceptual_weight = CFG.PERCEPTUAL_WEIGHT if perceptual_weight is None else perceptual_weight

    # Perceptual loss (NEW) only makes sense when the decoder's target IS a
    # real image (use_encryption=False) -- in the encrypted pipeline the
    # target is RS-encoded ciphertext bytes (pure noise), and VGG features
    # of noise carry no meaningful signal.
    apply_perceptual = use_perceptual_loss and not use_encryption
    if apply_perceptual:
        print(f"[train] Perceptual (VGG) loss ENABLED, weight={perceptual_weight} -- "
              f"first call downloads pretrained VGG16 weights if not already cached.")

    # NEW: default checkpoint filename depends on the mode, so an
    # encrypted+RS run and a plain (perceptual) run never overwrite each
    # other unless you explicitly ask them to share a name.
    if checkpoint_name is None:
        checkpoint_name = ("qgan_stego_checkpoint.pt" if use_encryption
                            else "qgan_stego_checkpoint_plain.pt")

    encoder = Encoder().to(DEVICE)
    decoder = Decoder().to(DEVICE)
    discriminator = Discriminator().to(DEVICE)

    # RESUME FEATURE (NEW): lets a run pick up exactly where a previous
    # checkpoint left off instead of starting from random weights again.
    # `epochs` now always means "how many MORE epochs to run from here" --
    # for a fresh run that's the same as "epochs" always meant (start_epoch=0),
    # so nothing changes if you don't pass resume_from.
    #
    # resume_from=True         -> auto-resume from this mode's default checkpoint
    #                              (checkpoints/qgan_stego_checkpoint.pt or
    #                              ..._plain.pt, whichever `use_encryption` implies)
    # resume_from="some/path"  -> resume from an explicit checkpoint file
    # resume_from=None         -> normal fresh-start behaviour (unchanged)
    start_epoch = 0
    history = {"reconstruction": [], "image_quality": [], "adversarial": [], "discriminator": [], "perceptual": []}
    if resume_from:
        ckpt_path = resume_from if isinstance(resume_from, str) else \
            os.path.join(CFG.CHECKPOINT_DIR, checkpoint_name)
        if os.path.exists(ckpt_path):
            print(f"[resume] Loading checkpoint from {ckpt_path} ...")
            ckpt = torch.load(ckpt_path, map_location=DEVICE)
            encoder.load_state_dict(ckpt["encoder"])
            decoder.load_state_dict(ckpt["decoder"])
            discriminator.load_state_dict(ckpt["discriminator"])
            history = ckpt.get("history", history)
            start_epoch = ckpt.get("last_completed_epoch", 0)
            print(f"[resume] Resumed at epoch {start_epoch} (weights + history loaded). "
                  f"Training {epochs} MORE epoch(s) -> will finish at epoch {start_epoch + epochs}.")
        else:
            print(f"[resume] WARNING: no checkpoint found at {ckpt_path} -- "
                  f"starting fresh from epoch 0 instead.")

    # RECONSTRUCTION CURRICULUM (NEW): from epoch 1, the encoder/decoder were
    # being asked to balance THREE competing goals at once -- exact secret
    # recovery, staying close to the cover, AND fooling the discriminator.
    # With byte-exact recovery of encrypted (noise-like) data already being
    # a very hard target, splitting the network's attention across all three
    # from the start makes it harder still. For the first `gamma_warmup_epochs`
    # epochs, the adversarial term is switched off entirely (effective
    # gamma=0) so the encoder/decoder can focus purely on nailing
    # reconstruction; the discriminator still trains normally throughout
    # (so it isn't behind once the adversarial term switches on at full
    # strength). Set gamma_warmup_epochs=0 to disable this and match the
    # old always-on behaviour.
    if gamma_warmup_epochs > 0:
        print(f"[train] Reconstruction warm-up: adversarial loss (gamma) will be "
              f"OFF for the first {gamma_warmup_epochs} epoch(s), then switch on "
              f"at gamma={gamma}.")

    if residual_strength is not None:
        encoder.residual_strength = residual_strength
        print(f"[train] Overriding RESIDUAL_STRENGTH -> {residual_strength} "
              f"(config.py default is {CFG.RESIDUAL_STRENGTH})")

    opt_ed = optim.Adam(list(encoder.parameters()) + list(decoder.parameters()),
                         lr=CFG.LR_ENCODER_DECODER)
    opt_disc = optim.Adam(discriminator.parameters(), lr=CFG.LR_DISCRIMINATOR)

    mse = nn.MSELoss()
    bce = nn.BCELoss()

    # Cover images: still fresh every batch via the normal dataloader (cheap, no RS involved)
    dataloader = get_dataloader(use_synthetic=use_synthetic, folder_path=folder_path,
                                 batch_size=batch_size, image_size=image_size)

    security = setup_security_layer() if use_encryption else {"aes_key": None}
    key = security["aes_key"]

    encoding_meta = {}
    secret_cache = None
    valid_mask = None  # NEW: marks which positions of secret_input are real data vs zero-padding

    if use_encryption:
        secret_cache = build_secret_cache(
            key, image_size, pool_size=secret_pool_size,
            use_synthetic=use_synthetic, folder_path=folder_path
        )
        encoding_meta.update(small_shape=secret_cache["small_shape"],
                              protected_length=secret_cache["protected_length"],
                              redundancy=secret_cache["redundancy"])
        pool_n = secret_cache["encoded"].shape[0]

        # BUG FIX (NEW): encrypt_image_array_protected() pads the encoded
        # secret with zeros to fill the full (C, H, W) tensor -- for the
        # default config that padding is OVER HALF the tensor (only
        # protected_length * redundancy positions out of C*H*W are real
        # data). mse(decoded, secret_input) was averaging over the WHOLE
        # tensor, so the model could get a great-looking loss number just
        # by learning to output near-zero on the (trivial, always-zero)
        # padded region, while the actual payload -- the part that
        # matters for exact byte recovery -- stayed poorly reconstructed.
        # This mask restricts the reconstruction loss to only the real
        # data positions, so the loss number (and the gradient) actually
        # reflects payload recovery quality.
        c, h, w = secret_cache["encoded"].shape[1:]
        valid_length = secret_cache["protected_length"] * secret_cache["redundancy"]
        mask_flat = torch.zeros(c * h * w)
        mask_flat[:valid_length] = 1.0
        valid_mask = mask_flat.reshape(c, h, w).to(DEVICE)
        valid_fraction = valid_length / (c * h * w)
        print(f"[train] Reconstruction loss will be computed on the real payload only "
              f"({valid_length}/{c*h*w} = {valid_fraction*100:.1f}% of the tensor; "
              f"the rest is zero-padding and is excluded so it can't dilute the loss).")

    for epoch in range(start_epoch, start_epoch + epochs):
        # Warm-up (NEW): gamma is 0 during the warm-up window, full value after.
        # Uses the ABSOLUTE epoch number, so if warm-up already finished before
        # a resume, it correctly stays off instead of re-triggering.
        effective_gamma = 0.0 if epoch < gamma_warmup_epochs else gamma

        for cover, dataloader_secret in dataloader:
            cover = cover.to(DEVICE)
            actual_batch_size = cover.shape[0]

            if use_encryption:
                # Sample from the pre-encoded pool instead of encoding fresh
                idxs = np.random.randint(0, pool_n, size=actual_batch_size)
                secret = secret_cache["secrets"][idxs].to(DEVICE)
                secret_input = secret_cache["encoded"][idxs].to(DEVICE)
            else:
                secret = dataloader_secret.to(DEVICE)
                secret_input = secret

            # ---------------- Train Encoder + Decoder ----------------
            stego = encoder(cover, secret_input)
            decoded = decoder(stego)

            if valid_mask is not None:
                # Masked MSE (NEW): only the real-payload positions count,
                # see the bug-fix note above.
                squared_error = (decoded - secret_input) ** 2
                reconstruction_loss = (squared_error * valid_mask).sum() / (
                    valid_mask.sum() * actual_batch_size
                )
            else:
                reconstruction_loss = mse(decoded, secret_input)
            image_quality_loss = mse(stego, cover)

            # Perceptual loss (NEW) -- compares VGG feature maps of the
            # decoded output against the true secret, instead of raw
            # pixels. This directly targets the "confident but wrong
            # color/texture on unfamiliar content" failure mode that
            # plain per-pixel MSE is prone to.
            if apply_perceptual:
                perc_loss = perceptual_loss(decoded, secret)
            else:
                perc_loss = torch.tensor(0.0, device=DEVICE)

            disc_pred_on_stego = discriminator(stego)
            adversarial_loss = bce(disc_pred_on_stego, torch.zeros_like(disc_pred_on_stego))

            total_ed_loss = (alpha * reconstruction_loss +
                              beta * image_quality_loss +
                              effective_gamma * adversarial_loss +
                              perceptual_weight * perc_loss)

            opt_ed.zero_grad()
            total_ed_loss.backward()
            opt_ed.step()

            # ---------------- Train Discriminator ----------------
            real_pred = discriminator(cover)
            fake_pred = discriminator(stego.detach())

            disc_loss = (bce(real_pred, torch.zeros_like(real_pred)) +
                         bce(fake_pred, torch.ones_like(fake_pred)))

            opt_disc.zero_grad()
            disc_loss.backward()
            opt_disc.step()

        history["reconstruction"].append(reconstruction_loss.item())
        history["image_quality"].append(image_quality_loss.item())
        history["adversarial"].append(adversarial_loss.item())
        history["discriminator"].append(disc_loss.item())
        history["perceptual"].append(perc_loss.item())

        print(f"Epoch {epoch + 1}/{start_epoch + epochs} | "
              f"Recon: {reconstruction_loss.item():.4f} | "
              f"ImgQuality: {image_quality_loss.item():.4f} | "
              f"Adv: {adversarial_loss.item():.4f} | "
              f"Disc: {disc_loss.item():.4f}"
              f"{f' | Perceptual: {perc_loss.item():.4f}' if apply_perceptual else ''}"
              f"{' | [gamma warm-up: OFF]' if effective_gamma == 0.0 and gamma_warmup_epochs > 0 else ''}")

        # PERIODIC checkpoint (NEW) -- every `checkpoint_every` epochs, so a
        # long run that gets interrupted loses at most that many epochs'
        # worth of progress, not the entire run.
        if save_checkpoint and checkpoint_every and (epoch + 1) % checkpoint_every == 0:
            _save_checkpoint(encoder, decoder, discriminator, history, epoch=epoch + 1,
                              checkpoint_name=checkpoint_name)

    if save_checkpoint:
        _save_checkpoint(encoder, decoder, discriminator, history, epoch=start_epoch + epochs,
                          checkpoint_name=checkpoint_name)

    return encoder, decoder, discriminator, security, history, encoding_meta


if __name__ == "__main__":
    import time
    start = time.time()
    train(epochs=3, batch_size=4, image_size=64, use_synthetic=True, secret_pool_size=16)
    print(f"\nTotal smoke test time: {time.time() - start:.1f} seconds")