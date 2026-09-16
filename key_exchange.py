
"""
key_exchange.py
----------------
RSA hybrid key exchange -- solves "how does the receiver safely get the AES
key" without ever transmitting the raw key.
"""
 
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
 
 
def generate_receiver_keypair(key_size: int = 2048):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()
    return private_key, public_key
 
 
def wrap_aes_key(aes_key: bytes, receiver_public_key) -> bytes:
    return receiver_public_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None),
    )
 
 
def unwrap_aes_key(wrapped_key: bytes, receiver_private_key) -> bytes:
    return receiver_private_key.decrypt(
        wrapped_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None),
    )
 
 
# ==================== Persisting keys to disk  ====================

 
def serialize_private_key(private_key, path: str, password: bytes = None):
    """
    Saves the receiver's private key to a PEM file. In this demo it's
    unencrypted at rest (password=None); pass a bytes password to encrypt
    it instead. Either way: this file must NEVER be given to a sender or
    leave the receiver's machine -- it's the only thing that can unwrap a
    message's AES key.
    """
    encryption = (serialization.BestAvailableEncryption(password)
                  if password else serialization.NoEncryption())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    with open(path, "wb") as f:
        f.write(pem)
 
 
def serialize_public_key(public_key, path: str):
    """Saves the receiver's public key. This one IS meant to be handed to senders."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(path, "wb") as f:
        f.write(pem)
 
 
def load_private_key(path: str, password: bytes = None):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=password)
 
 
def load_public_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())
 
 
if __name__ == "__main__":
    priv, pub = generate_receiver_keypair()
    fake_key = bytes(range(16))
    wrapped = wrap_aes_key(fake_key, pub)
    recovered = unwrap_aes_key(wrapped, priv)
    print("Round-trip correct:", recovered == fake_key)
 
    print("\n--- PEM save/load round-trip ---")
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        priv_path = os.path.join(tmp, "priv.pem")
        pub_path = os.path.join(tmp, "pub.pem")
        serialize_private_key(priv, priv_path)
        serialize_public_key(pub, pub_path)
        priv2 = load_private_key(priv_path)
        pub2 = load_public_key(pub_path)
        wrapped2 = wrap_aes_key(fake_key, pub2)
        recovered2 = unwrap_aes_key(wrapped2, priv2)
        print("Round-trip correct after PEM save/load:", recovered2 == fake_key)
 
