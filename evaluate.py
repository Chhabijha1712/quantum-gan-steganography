"""
evaluate.py
-----------
Metrics for your Results slide, now using the Reed-Solomon-protected
decode path: average redundant copies -> RS-correct remaining errors ->
AES-decrypt -> compare to the true (downscaled) secret.
"""

import io
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim
from sklearn.metrics import accuracy_score

from config import CFG
from crypto_utils import decrypt_image_array_protected


def tensor_to_uint8(tensor: torch.Tensor) -> np.ndarray:
    return ((tensor.clamp(-1, 1) + 1) * 127.5).byte().cpu().numpy()


def evaluate_image_quality(cover_tensor, stego_tensor):
    cover_arr = tensor_to_uint8(cover_tensor).transpose(1, 2, 0)
    stego_arr = tensor_to_uint8(stego_tensor).transpose(1, 2, 0)
    p = psnr(cover_arr, stego_arr, data_range=255)
    s = ssim(cover_arr, stego_arr, channel_axis=2, data_range=255)
    return p, s


def evaluate_secret_recovery_protected(original_secret_tensor, decoded_tensor,
                                        key, nonce, encoding_meta, pixel_tolerance=8):
    """
    Decodes through the full Reed-Solomon-protected pipeline. If RS
    correction succeeds, exact_bit_accuracy will be 100% (or very close) --
    that's the whole point of using RS instead of pure averaging. If RS
    correction FAILS (too many corrupted bytes for its capacity), this
    raises an exception rather than silently returning garbage -- that's
    useful signal, not a bug: it tells you the raw error rate is still
    too high for the current RS_NSYM/redundancy settings.
    """
    original_arr = tensor_to_uint8(original_secret_tensor)
    decoded_arr = tensor_to_uint8(decoded_tensor)

    try:
        recovered_small = decrypt_image_array_protected(
            decoded_arr, key, nonce,
            small_shape=encoding_meta["small_shape"],
            protected_length=encoding_meta["protected_length"],
            redundancy=encoding_meta["redundancy"],
            nsym=CFG.RS_NSYM,
        )
        rs_correction_succeeded = True
    except Exception as e:
        print(f"[evaluate] Reed-Solomon correction failed ({e}) -- raw error rate "
              f"exceeded RS_NSYM={CFG.RS_NSYM}'s correction capacity. Try raising "
              f"RS_NSYM or RS_REDUNDANCY in config.py.")
        recovered_small = np.zeros(encoding_meta["small_shape"], dtype=np.uint8)
        rs_correction_succeeded = False

    from PIL import Image as PILImage
    small_shape = encoding_meta["small_shape"]
    orig_img = PILImage.fromarray(original_arr.transpose(1, 2, 0))
    orig_small = np.array(orig_img.resize((small_shape[2], small_shape[1]), PILImage.BOX)).transpose(2, 0, 1)

    if rs_correction_succeeded:
        p = psnr(orig_small.transpose(1, 2, 0), recovered_small.transpose(1, 2, 0), data_range=255)
        s = ssim(orig_small.transpose(1, 2, 0), recovered_small.transpose(1, 2, 0), channel_axis=2, data_range=255)
    else:
        p, s = 0.0, 0.0

    exact_bit_accuracy = float(np.mean(orig_small == recovered_small))
    pixel_diff = np.abs(orig_small.astype(int) - recovered_small.astype(int))
    tolerant_accuracy = float(np.mean(pixel_diff <= pixel_tolerance))

    return p, s, exact_bit_accuracy, tolerant_accuracy, rs_correction_succeeded


def evaluate_detection_accuracy(discriminator, cover_batch, stego_batch, device):
    discriminator.eval()
    with torch.no_grad():
        cover_preds = discriminator(cover_batch.to(device)).cpu().numpy().flatten()
        stego_preds = discriminator(stego_batch.to(device)).cpu().numpy().flatten()

    true_labels = np.concatenate([np.zeros(len(cover_preds)), np.ones(len(stego_preds))])
    pred_labels = (np.concatenate([cover_preds, stego_preds]) > 0.5).astype(int)
    return accuracy_score(true_labels, pred_labels)


if __name__ == "__main__":
    from train import train, encrypt_batch_secrets, DEVICE
    from dataset import get_dataloader

    encoder, decoder, discriminator, security, history, encoding_meta = train(
        epochs=3, batch_size=4, image_size=64, use_synthetic=True, use_encryption=True
    )
    key = security["aes_key"]

    dataloader = get_dataloader(use_synthetic=True, batch_size=4, image_size=64)
    cover, secret = next(iter(dataloader))
    cover, secret = cover.to(DEVICE), secret.to(DEVICE)

    secret_input, nonces, small_shape, protected_length, redundancy = encrypt_batch_secrets(secret, key)
    secret_input = secret_input.to(DEVICE)
    encoding_meta = dict(small_shape=small_shape, protected_length=protected_length, redundancy=redundancy)

    encoder.eval()
    decoder.eval()
    with torch.no_grad():
        stego = encoder(cover, secret_input)
        decoded = decoder(stego)

    p_img, s_img = evaluate_image_quality(cover[0], stego[0])
    print(f"Cover vs Stego   -> PSNR: {p_img:.2f} dB | SSIM: {s_img:.4f}")

    p_sec, s_sec, exact_acc, tolerant_acc, rs_ok = evaluate_secret_recovery_protected(
        secret[0], decoded[0], key, nonces[0], encoding_meta
    )
    print(f"Secret Recovery  -> PSNR: {p_sec:.2f} dB | SSIM: {s_sec:.4f} | "
          f"Exact accuracy: {exact_acc*100:.2f}% | RS correction succeeded: {rs_ok}")

    det_acc = evaluate_detection_accuracy(discriminator, cover, stego, DEVICE)
    print(f"Detection Accuracy: {det_acc*100:.2f}%")
