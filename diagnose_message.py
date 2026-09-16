"""
diagnose_message.py  (NEW FILE)
---------------------------------
receive.py's failure message tells you Reed-Solomon's correction capacity
was exceeded, but not by how much, or whether the errors are spread evenly
or concentrated in a few blocks (which matters -- RS fails hard on ANY
single 255-byte block that exceeds its capacity, even if every other
block is perfect). This script answers that precisely, using
crypto_utils.diagnose_raw_error_rate() -- the same diagnostic the Colab
notebook had (Section 8b), adapted here for the real send.py/receive.py
file-based flow instead of in-memory tensors.

IMPORTANT: this needs the TRUE original secret image to compare against --
something only the sender/tester has, never a real receiver. This script
is for YOU to debug the pipeline locally, not something a real receiver
would ever run (a real receiver has no way to know the true secret --
that's the whole point of hiding it).

Usage:
    python diagnose_message.py --stego messages/message1_stego.png \\
        --package messages/message1_package.json \\
        --receiver-private-key keys/receiver_private_key.pem \\
        --original-secret dataset/DIV2K_valid_HR/0833.png
"""

import json
import base64
import argparse

import numpy as np
import torch

from config import CFG
from checkpoint_utils import load_models_checkpoint
from image_io import load_image_as_tensor
from crypto_utils import compute_ground_truth_protected, diagnose_raw_error_rate
from key_exchange import load_private_key, unwrap_aes_key


def _tensor_to_uint8_array(tensor):
    return ((tensor.clamp(-1, 1) + 1) * 127.5).byte().cpu().numpy()


def main():
    parser = argparse.ArgumentParser(
        description="Debug tool: measure the real channel error rate for one message."
    )
    parser.add_argument("--stego", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--receiver-private-key", required=True)
    parser.add_argument("--original-secret", required=True,
                        help="The TRUE secret image used at send time (for debugging only)")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    with open(args.package) as f:
        package = json.load(f)

    wrapped_key = base64.b64decode(package["wrapped_aes_key_b64"])
    nonce = base64.b64decode(package["nonce_b64"])
    small_shape = tuple(package["small_shape"])
    protected_length = package["protected_length"]
    redundancy = package["redundancy"]
    rs_nsym = package["rs_nsym"]
    image_size = package.get("image_size", CFG.IMAGE_SIZE)

    print("[diagnose] Unwrapping AES key with receiver's private key...")
    receiver_private_key = load_private_key(args.receiver_private_key)
    aes_key = unwrap_aes_key(wrapped_key, receiver_private_key)

    print("[diagnose] Loading decoder and running it on the stego image...")
    _encoder, decoder, _discriminator = load_models_checkpoint(device=device)
    stego_tensor = load_image_as_tensor(args.stego, image_size).to(device)
    with torch.no_grad():
        decoded_tensor = decoder(stego_tensor)
    decoded_arr = _tensor_to_uint8_array(decoded_tensor[0])

    print("[diagnose] Recomputing the TRUE protected bytes from the original secret...")
    original_tensor = load_image_as_tensor(args.original_secret, image_size)
    original_arr = _tensor_to_uint8_array(original_tensor[0])
    ground_truth = compute_ground_truth_protected(
        original_arr, aes_key, nonce,
        downscale_factor=CFG.SECRET_DOWNSCALE_FACTOR, nsym=rs_nsym,
    )

    diag = diagnose_raw_error_rate(
        decoded_arr, ground_truth,
        protected_length=protected_length, redundancy=redundancy, nsym=rs_nsym,
    )

    print(f"\nOverall raw byte error rate (after averaging, before RS): {diag['overall_error_rate']*100:.2f}%")
    print(f"Total errors: {diag['total_errors']} / {diag['total_bytes']} bytes")
    print(f"RS correction capacity per block: {diag['correction_capacity_per_block']} bytes (out of 255)")
    print(f"Any block exceeds capacity: {diag['any_block_exceeds_capacity']}")
    print(f"\nPer-block breakdown:")
    for r in diag["block_reports"]:
        marker = " <-- EXCEEDS CAPACITY" if r["would_fail_this_block"] else ""
        print(f"  Block {r['block']}: {r['errors']}/{r['block_size']} errors "
              f"(capacity {r['capacity']}){marker}")

    print("\n[diagnose] What to do next:")
    if diag["overall_error_rate"] < 0.05:
        print("  Error rate is fairly low but concentrated in specific blocks -- "
              "raising RS_REDUNDANCY in config.py (more averaging before RS has "
              "to correct) is likely to fix this without retraining.")
    elif diag["overall_error_rate"] < 0.20:
        print("  Moderate error rate -- try raising RS_NSYM (more parity bytes, "
              "more correction capacity per block) in config.py and retrain.")
    else:
        print("  High error rate -- redundancy/RS tuning alone won't fix this. "
              "The GAN itself isn't reconstructing accurately enough yet: train "
              "for more epochs, and/or on more images (100 is a small dataset "
              "for 128x128 real photos), then re-run this diagnostic.")


if __name__ == "__main__":
    main()