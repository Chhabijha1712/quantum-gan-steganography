# 🔐 Quantum-Assisted Steganography with GAN-Based Hiding

A hybrid steganography system that combines **quantum-assisted key generation**, **RSA + AES cryptography**, and a **GAN-based encoder/decoder** to hide a secret image inside a cover image — imperceptibly, securely, and recoverably.

The secret is never hidden in the clear: it's first **encrypted** (quantum-seeded key → RSA key exchange → AES-CTR), **protected with Reed-Solomon error correction**, and only then **embedded** into the cover image by a neural encoder trained adversarially against a discriminator that tries to detect it.

---

## ✨ Features

| Component | Description |
|---|---|
| 🎲 **Quantum Key Generation** | Seeds the encryption key using quantum-derived randomness |
| 🔑 **RSA-2048 Key Exchange** | The AES key is wrapped with the receiver's RSA public key, so only the intended receiver can unwrap it |
| 🛡️ **AES-128 (CTR) Encryption** | The secret image is encrypted before it ever touches the steganography pipeline |
| 🧠 **GAN-Based Steganography** | An Encoder/Decoder network learns to hide and recover the encrypted payload inside a cover image |
| ⚔️ **Adversarial Discriminator Training** | A discriminator is trained to detect stego images, pushing the encoder to make them statistically indistinguishable from clean covers |
| 🧩 **Reed-Solomon Error Correction** | Adds parity bytes so the encrypted payload can be recovered exactly, even after neural-network reconstruction noise |
| 📊 **PSNR / SSIM Metrics** | Every recovery is scored for both cryptographic exact-match quality and perceptual stego image quality |
| 🖥️ **Streamlit Demo App** | End-to-end interactive UI — pick a cover + secret image, generate keys, hide, and recover |

---

## 🏗️ How It Works

```
Secret Image
     │
     ▼
[Quantum-seeded AES-128 Encryption] ──► Encrypted payload (looks like noise)
     │
     ▼
[Reed-Solomon Encoding]  ──► Adds redundancy for exact-recovery guarantees
     │
     ▼
[GAN Encoder]  +  Cover Image ──► Stego Image (visually ≈ Cover Image)
     │
     ▼
      ... transmitted / shared ...
     │
     ▼
[GAN Decoder] ──► Recovered encrypted payload
     │
     ▼
[Reed-Solomon Decoding] ──► Corrects residual bit errors
     │
     ▼
[RSA-Unwrapped AES Key] ──► [AES Decryption] ──► Recovered Secret Image
```

Two recoveries are always shown side by side:
- **Exact Recovery** — the cryptographic path (pixel-perfect once decryption succeeds)
- **Approximate Recovery** — the raw GAN decoder output (shows how well the neural network alone learned to reconstruct the payload)

---

## 📁 Project Structure

```
├── config.py                  # ALL tunable settings (single source of truth)
├── train.py                   # GAN training loop (supports checkpoint resume)
├── models.py                  # Encoder / Decoder / Discriminator architectures
├── crypto_utils.py            # AES, RSA, Reed-Solomon helpers
├── setup_receiver_identity.py # Generates receiver RSA keypair
├── send.py / receive.py       # CLI scripts for the real sender/receiver flow
├── streamlit_app.py           # Interactive demo UI
├── checkpoints/               # Saved model weights (generated during training)
├── keys/                      # Receiver RSA keypair (⚠️ never commit real keys)
├── messages/                  # stego.png + package.json per sent message
└── dataset/                   # DIV2K or other cover/secret image source
```

---

## ⚙️ Setup

```bash
# Clone the repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

---

## 🏋️ Training

All hyperparameters live in `config.py` — edit them there, or override per-run:

```bash
python -c "from train import train; train(use_encryption=False, epochs=60, use_perceptual_loss=False)"
```

### Resume from a checkpoint

Training can be safely stopped and resumed — no progress is lost:

```bash
python -c "from train import train; train(use_encryption=False, epochs=40, use_perceptual_loss=False, resume_from=True)"
```

`epochs` always means **"how many additional epochs to run from here."**

---

## 🚀 Running the Demo

```bash
streamlit run streamlit_app.py
```

Upload a cover image and a secret image, generate a receiver identity, hide the secret, and recover it — PSNR and SSIM are computed automatically for both the exact and approximate recovery paths.

---

## 📊 Sample Results

| Metric | Value |
|---|---|
| PSNR (Stego Recovery) | **20.75 dB** |
| SSIM (Stego Recovery) | **0.858** |

> The **Exact Recovery** (cryptographic path) is always pixel-perfect once decryption succeeds — the numbers above refer to the neural **Approximate Recovery** path (raw GAN decoder output), which now reconstructs the secret's structure, colors, and layout with high fidelity.

---

## 🗺️ Roadmap

- [ ] Further sharpen GAN reconstruction (reduce residual blur) with extended perceptual-loss fine-tuning
- [ ] Benchmark reconstruction quality across larger, more diverse datasets
- [ ] Add automated hyperparameter logging per checkpoint
- [ ] Deploy public demo (Streamlit Community Cloud / Hugging Face Spaces)

---

## 🛠️ Tech Stack

- **PyTorch** — GAN training (Encoder, Decoder, Discriminator)
- **Streamlit** — interactive demo UI
- **PyCryptodome** — AES / RSA cryptography
- **Reed-Solomon (reedsolo)** — error correction coding
- **NumPy / Pillow** — image processing

---

## ⚠️ Security Note

This is an academic/research project demonstrating the intersection of cryptography and neural steganography. The `keys/` folder contains real RSA key material when generated locally — **never commit real keys to a public repository.**

---

## 📄 License

MIT — feel free to use, modify, and build on this project.
