import os
import torch

from config import CFG
from models import Encoder, Decoder, Discriminator


def load_models_checkpoint(path: str = None, device=None, checkpoint_name: str = "qgan_stego_checkpoint.pt"):
    """
    Returns (encoder, decoder, discriminator), all already in .eval() mode,
    with weights loaded from the checkpoint train.py saved (the dict with
    keys "encoder", "decoder", "discriminator", "history").

    checkpoint_name (NEW): train.py can save two separate checkpoints --
    "qgan_stego_checkpoint.pt" (full encrypted+Reed-Solomon security
    pipeline) and "qgan_stego_checkpoint_plain.pt" (plain, no-encryption
    run trained for perceptual image-in-image hiding quality). Pass the
    one you want; ignored if you pass an explicit `path`.

    Raises a clear, actionable error (not a cryptic torch traceback) if no
    checkpoint exists yet -- that means train.py hasn't been run, which is
    a different problem from anything being broken in this file.
    """
    path = path or os.path.join(CFG.CHECKPOINT_DIR, checkpoint_name)
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No trained checkpoint found at '{path}'. Run train.py first "
            f"(it saves this file automatically when save_checkpoint=True, "
            f"which is the default) -- send.py / receive.py only ever LOAD "
            f"an already-trained model, they never train one themselves."
        )

    checkpoint = torch.load(path, map_location=device)

    encoder = Encoder().to(device)
    decoder = Decoder().to(device)
    discriminator = Discriminator().to(device)

    encoder.load_state_dict(checkpoint["encoder"])
    decoder.load_state_dict(checkpoint["decoder"])
    discriminator.load_state_dict(checkpoint["discriminator"])

    encoder.eval()
    decoder.eval()
    discriminator.eval()

    return encoder, decoder, discriminator