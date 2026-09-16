"""
receive.py — FINAL real-world receiver
------------------------------------------
Reverses send.py's two independent layers:
  1. RSA-unwraps the AES key with the receiver's OWN private key
  2. AES-decrypts <name>_secret.enc -- EXACT, byte-for-byte original
     secret (the cryptographic confidentiality guarantee -- always exact)
  3. GAN-decodes <name>_stego.png -- an approximate recovered secret via
     steganography (visual quality, PSNR/SSIM measured against the exact
     version from step 2 -- which a real receiver genuinely has at this
     point, so this comparison is completely legitimate)

Usage:
    python receive.py --stego messages/final_stego.png \\
        --secret-enc messages/final_secret.enc \\
        --package messages/final_package.json \\
        --receiver-private-key keys/receiver_private_key.pem \\
        --out-name final
"""

import os
import json
import base64
import zipfile
import tempfile
import argparse

import torch
from PIL import Image

from config import CFG
from checkpoint_utils import load_models_checkpoint
from image_io import load_image_as_tensor, save_tensor_as_image
from evaluate import evaluate_image_quality
from crypto_utils import decrypt_to_image_array
from key_exchange import load_private_key, unwrap_aes_key


def receive(message_bundle_path: str, receiver_private_key_path: str,
            out_name: str, messages_dir: str = None):
    messages_dir = messages_dir or CFG.MESSAGES_DIR
    os.makedirs(messages_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"[receive] Unpacking message bundle: {message_bundle_path}")
    extract_dir = os.path.join(messages_dir, f"{out_name}_unpacked")
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(message_bundle_path, "r") as zf:
        zf.extractall(extract_dir)

    stego_path = os.path.join(extract_dir, "stego.png")
    secret_enc_path = os.path.join(extract_dir, "secret.enc")
    package_path = os.path.join(extract_dir, "package.json")

    print(f"[receive] Loading package...")
    with open(package_path) as f:
        package = json.load(f)
    wrapped_key = base64.b64decode(package["wrapped_aes_key_b64"])
    nonce = base64.b64decode(package["nonce_b64"])
    secret_shape = tuple(package["secret_shape"])
    image_size = package.get("image_size", CFG.IMAGE_SIZE)

    print(f"[receive] Unwrapping the AES key with the receiver's private key: {receiver_private_key_path}")
    receiver_private_key = load_private_key(receiver_private_key_path)
    aes_key = unwrap_aes_key(wrapped_key, receiver_private_key)

    # ---- Cryptographic recovery: EXACT, guaranteed ----
    print(f"[receive] AES-decrypting {secret_enc_path} (exact recovery)...")
    with open(secret_enc_path, "rb") as f:
        ciphertext = f.read()
    exact_secret_arr = decrypt_to_image_array(ciphertext, aes_key, nonce, shape=secret_shape)
    exact_path = os.path.join(messages_dir, f"{out_name}_exact_recovered_secret.png")
    Image.fromarray(exact_secret_arr.transpose(1, 2, 0)).save(exact_path)
    print(f"[receive] Exact (cryptographic) recovery saved: {exact_path}")

    # ---- Steganographic recovery: approximate, via the GAN ----
    print("[receive] Loading trained decoder (steganography model)...")
    _encoder, decoder, _discriminator = load_models_checkpoint(
        device=device, checkpoint_name="qgan_stego_checkpoint_plain.pt"
    )
    print(f"[receive] Loading stego image: {stego_path}")
    stego_tensor = load_image_as_tensor(stego_path, image_size).to(device)
    with torch.no_grad():
        decoded_tensor = decoder(stego_tensor)
    stego_recovered_path = os.path.join(messages_dir, f"{out_name}_stego_recovered_secret.png")
    save_tensor_as_image(decoded_tensor[0], stego_recovered_path)
    print(f"[receive] Steganographic (approximate) recovery saved: {stego_recovered_path}")

    
    exact_tensor = torch.from_numpy(
        exact_secret_arr.astype("float32") / 127.5 - 1.0
    ).unsqueeze(0).to(device)
    p_sec, s_sec = evaluate_image_quality(exact_tensor[0], decoded_tensor[0])
    print(f"\n[receive] Steganographic recovery vs exact secret -> "
          f"PSNR: {p_sec:.2f} dB | SSIM: {s_sec:.4f}")

    return exact_path, stego_recovered_path


def main():
    parser = argparse.ArgumentParser(
        description="Recover a secret image: crypto-exact + stego-approximate."
    )
    parser.add_argument("--message", required=True, help="Path to the .qsteg bundle from send.py")
    parser.add_argument("--receiver-private-key", required=True)
    parser.add_argument("--out-name", default="message")
    parser.add_argument("--messages-dir", default=None)
    args = parser.parse_args()
    receive(args.message, args.receiver_private_key, args.out_name, args.messages_dir)


if __name__ == "__main__":
    main()