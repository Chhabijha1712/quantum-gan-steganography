"""
image_io.py  (NEW FILE)
-----------------------
Real image file <-> tensor conversion. Everything in the existing project
worked on batches of tensors that dataset.py generated (synthetic noise or
resized DIV2K images) -- there was no code path for "a user's own cover.jpg
and secret.jpg on disk". This file is that path; send.py and receive.py
both import it.
"""

import numpy as np
import torch
from PIL import Image


def load_image_as_tensor(path: str, image_size: int) -> torch.Tensor:
    """
    Loads any image file (jpg/png/webp/...), converts to RGB, CENTER-CROPS
    to a square (so a rectangular photo isn't squished/distorted -- the
    crop keeps the largest possible square from the middle of the image),
    then resizes to (image_size, image_size) -- the model only ever saw
    this fixed size during training, so both cover and secret MUST be
    resized to it -- and normalizes to [-1, 1], the same convention
    dataset.py uses. Returns a (1, 3, H, W) tensor (batch size 1) ready to
    feed the encoder/decoder.
    """
    img = Image.open(path).convert("RGB")


    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))

    img = img.resize((image_size, image_size), Image.BICUBIC)
    arr = np.array(img).astype(np.float32) / 127.5 - 1.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Single image tensor, shape (3, H, W) or (1, 3, H, W), range [-1, 1] -> PIL Image."""
    if tensor.dim() == 4:
        tensor = tensor[0]
    arr = ((tensor.clamp(-1, 1) + 1) * 127.5).byte().cpu().numpy()
    return Image.fromarray(arr.transpose(1, 2, 0))


def save_tensor_as_image(tensor: torch.Tensor, path: str):
    """
    Saves a stego/recovered tensor to disk. ALWAYS as lossless .png -- a
    JPEG re-save can destroy the hidden signal unless the corruption stays
    within the JPEG-robustness margin config.py's TEST_JPEG_QUALITY
    simulates during evaluation, and there's no guarantee of that for an
    arbitrary re-save (e.g. WhatsApp/Telegram/Instagram all recompress
    images). Refusing a non-.png path here catches that mistake early
    instead of producing a stego image that silently fails to decode.
    """
    if not path.lower().endswith(".png"):
        raise ValueError(
            f"Refusing to save '{path}' -- stego/recovered images must be saved "
            f"as lossless .png, not a lossy format. A JPEG re-save can destroy "
            f"the hidden data unless it happens to fall within the JPEG-robustness "
            f"margin tested in evaluate.py."
        )
    tensor_to_pil(tensor).save(path)


def save_array_as_image(arr: np.ndarray, path: str, upscale_to: int = None):
    """
    Saves a raw uint8 (C, H, W) array -- e.g. the recovered secret, which
    is naturally small because SECRET_DOWNSCALE_FACTOR shrinks it before
    hiding -- as a .png. If upscale_to is given, ALSO saves a second,
    upscaled copy purely for easier visual inspection in a demo/report;
    that upscaled copy is not "more recovered data", just a bigger picture
    of the same recovered pixels, and the filename says so.
    """
    if not path.lower().endswith(".png"):
        raise ValueError("Save recovered secrets as .png to avoid lossy artifacts.")
    img = Image.fromarray(arr.transpose(1, 2, 0))
    img.save(path)

    if upscale_to:
        upscaled_path = path.replace(".png", f"_upscaled_{upscale_to}px_for_viewing.png")
        img.resize((upscale_to, upscale_to), Image.NEAREST).save(upscaled_path)
        return path, upscaled_path
    return path, None