"""
setup_receiver_identity.py  (NEW FILE)
----------------------------------------
Run this ONCE per receiver, before any real message is ever sent to them --
exactly like generating a PGP or SSH keypair before anyone can encrypt
something for you. Produces:

  keys/receiver_private_key.pem  -- the receiver keeps this SECRET, forever.
  keys/receiver_public_key.pem   -- the receiver hands this to any sender
                                     (email it, post it, doesn't matter --
                                     it's supposed to be public).

send.py needs the *public* key file. receive.py needs the *private* key
file. Re-running this OVERWRITES both -- any message already encoded
against the old public key can then never be decoded again, so don't
re-run it casually once real messages exist.

Usage:
    python setup_receiver_identity.py
    python setup_receiver_identity.py --keys-dir keys
"""

import os
import argparse

from config import CFG
from key_exchange import generate_receiver_keypair, serialize_private_key, serialize_public_key


def main():
    parser = argparse.ArgumentParser(description="Generate the receiver's RSA identity keypair.")
    parser.add_argument("--keys-dir", default=CFG.KEYS_DIR)
    args = parser.parse_args()

    os.makedirs(args.keys_dir, exist_ok=True)
    private_path = os.path.join(args.keys_dir, "receiver_private_key.pem")
    public_path = os.path.join(args.keys_dir, "receiver_public_key.pem")

    if os.path.exists(private_path) or os.path.exists(public_path):
        confirm = input(
            f"Keys already exist in '{args.keys_dir}'. Overwriting will make any "
            f"message already encoded for the old public key permanently "
            f"undecodable. Type 'yes' to overwrite, anything else to abort: "
        )
        if confirm.strip().lower() != "yes":
            print("Aborted. Existing keys left untouched.")
            return

    private_key, public_key = generate_receiver_keypair(CFG.RSA_KEY_SIZE)
    serialize_private_key(private_key, private_path)
    serialize_public_key(public_key, public_path)

    print(f"[identity] Private key (keep secret):  {private_path}")
    print(f"[identity] Public key  (share freely): {public_path}")
    print("\nGive the public key file to anyone who wants to send you a message.")
    print("Never give anyone the private key file.")


if __name__ == "__main__":
    main()