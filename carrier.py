"""
carrier.py -- hide the .qsteg bundle INSIDE a normal PNG/JPEG image so the
message can be shared as an ordinary picture (Gmail, WhatsApp-as-document, ...).

Layout of the output image file:
    [ normal PNG / JPEG bytes ]  [ MAGIC_START | bundle bytes | 8-byte length | MAGIC_END ]

Every image viewer ignores bytes after the end of the image, so the picture
looks exactly like the stego image. The receiver reads the trailer back.
"""
import io
import struct

from PIL import Image

MAGIC_START = b"QSTEGv1\x00BEGIN"
MAGIC_END = b"QSTEGv1\x00END!!"


def make_carrier_image(stego_image_path, bundle_bytes, fmt="PNG", jpeg_quality=95):
    """Return (file_bytes, file_extension, mime) -- a viewable image carrying the bundle."""
    fmt = fmt.upper()
    img = Image.open(stego_image_path).convert("RGB")
    buf = io.BytesIO()
    if fmt in ("JPG", "JPEG"):
        img.save(buf, format="JPEG", quality=jpeg_quality, subsampling=0)
        ext, mime = "jpg", "image/jpeg"
    else:
        img.save(buf, format="PNG")
        ext, mime = "png", "image/png"

    payload = MAGIC_START + bundle_bytes + struct.pack(">Q", len(bundle_bytes)) + MAGIC_END
    return buf.getvalue() + payload, ext, mime


def extract_bundle_from_file(file_bytes):
    """Return the hidden bundle bytes, or None if the file carries no payload."""
    if not file_bytes.endswith(MAGIC_END):
        # Some apps add a few trailing bytes; search the tail instead.
        pos = file_bytes.rfind(MAGIC_END)
        if pos == -1:
            return None
        file_bytes = file_bytes[: pos + len(MAGIC_END)]
    len_end = len(file_bytes) - len(MAGIC_END)
    if len_end < 8:
        return None
    (n,) = struct.unpack(">Q", file_bytes[len_end - 8:len_end])
    start = len_end - 8 - n
    if start < len(MAGIC_START) or file_bytes[start - len(MAGIC_START):start] != MAGIC_START:
        return None
    return file_bytes[start:start + n]


def to_png_bytes(image_path):
    """Read any image file and return real PNG bytes (used for all recovered-image downloads)."""
    buf = io.BytesIO()
    Image.open(image_path).convert("RGB").save(buf, format="PNG")
    return buf.getvalue()