🔐 Quantum-Assisted GAN Steganography

🚀 Live Demo — Try it now

A hybrid steganography system that combines quantum-assisted key generation, RSA + AES cryptography, and a GAN-based encoder/decoder to hide a secret image inside a cover image — imperceptibly, securely, and recoverably.

The secret is never hidden in the clear: it's AES-encrypted (quantum-seeded key → RSA key exchange → AES-128 CTR) into a companion ciphertext file for guaranteed exact recovery, while a GAN encoder separately embeds the real secret image into the cover — trained adversarially against a discriminator — for an approximate but immediately viewable recovery. Two independent guarantees on the same secret: concealment and confidentiality.

✨ Features
Component	Description
🎲 Quantum Key Generation	Seeds the AES key using IBM Qiskit — Hadamard-gate qubit superposition and measurement; falls back to a classical secure RNG if unavailable
🔑 RSA-2048 Key Exchange	The AES key is wrapped with the receiver's RSA public key — only the intended receiver's private key (which never leaves their machine) can unwrap it
🛡️ AES-128 (CTR) Encryption	The secret image is encrypted into a companion file, independent of the steganographic channel
🧠 GAN-Based Steganography	An Encoder/Decoder network learns to hide and recover a secret image inside a cover image as a small residual perturbation
⚔️ Adversarial Discriminator Training	Pushes the Encoder toward stego images that are statistically indistinguishable from clean covers
🔀 Dual Recovery Path	Exact (AES decrypt — pixel-perfect) and Approximate (GAN decoder — perceptual) recoveries, always shown side by side
📊 PSNR / SSIM Metrics	Every GAN recovery is automatically scored for perceptual quality
🖥️ Three Interfaces	A deployed Streamlit web app, a Tkinter desktop app, and a full-stack FastAPI + React app with live SSE progress
🏗️ How It Works
Cover Image            Secret Image
     │                       │
     │                       ▼
     │         [Quantum-Seeded AES-128 Encryption] ──► secret.enc
     │                       │                          (unreadable without the key)
     │                       ▼
     │              [GAN Encoder]  ◄── trained adversarially
     ▼                       │          against a Discriminator
[Cover + Secret] ──────────► │
                              ▼
                        Stego Image  (visually ≈ Cover Image)
                              │
                 ... bundled into one .qsteg file,
                     transmitted over any public channel ...
                              │
              ┌───────────────┴───────────────┐
              ▼                                ▼
     [RSA-Unwrap + AES Decrypt]        [GAN Decoder]
              │                                │
              ▼                                ▼
     Exact Recovery                   Approximate Recovery
     (pixel-perfect)                  (PSNR / SSIM scored)

Two recoveries, always shown side by side:

Exact Recovery — the cryptographic path, pixel-perfect once decryption succeeds
Approximate Recovery — the raw GAN decoder output, showing how well the neural network alone reconstructs the payload
🧬 Model Architecture
Network	Role	Key Config
Encoder	Takes the cover + secret image, outputs a stego image via a learned residual perturbation	ENCODER_HIDDEN_CHANNELS, RESIDUAL_STRENGTH
Decoder	Takes the stego image alone and reconstructs the hidden secret	DECODER_HIDDEN_CHANNELS
Discriminator	Distinguishes stego images from clean covers; its feedback pushes the Encoder toward imperceptibility	DISCRIMINATOR_HIDDEN_CHANNELS

Combined loss function (all weights in config.py):

Total Loss = α · Reconstruction Loss + β · Image Quality Loss + γ · Adversarial Loss
Weight	Effect when increased
ALPHA_RECONSTRUCTION	Decoder recovers the secret more accurately
BETA_IMAGE_QUALITY	Stego image stays closer to the cover (less visible)
GAMMA_ADVERSARIAL	Harder for the discriminator to detect the stego image

An optional perceptual (VGG feature-space) loss can be enabled for the plain (non-encrypted) training mode — note its weight needs to be set roughly two orders of magnitude below the other terms, or it dominates training (see PERCEPTUAL_WEIGHT in config.py). Training also supports a reconstruction warm-up (adversarial loss stays off for the first few epochs) and data augmentation (center-square crop, random crop, horizontal flip, colour jitter).

📁 Project Structure
├── config.py                   # ALL tunable settings (single source of truth)
├── train.py                    # GAN training loop — supports checkpoint resume
├── models.py                   # Encoder / Decoder / Discriminator architectures
├── crypto_utils.py             # AES, Reed-Solomon helpers
├── key_exchange.py             # RSA wrap/unwrap + PEM save/load
├── quantum_key.py               # Qiskit quantum key generation
├── checkpoint_utils.py         # Loads a trained checkpoint for inference
├── image_io.py                 # Image file <-> tensor conversion
├── dataset.py                  # Training dataloader (DIV2K)
├── setup_receiver_identity.py  # CLI: generates the receiver's RSA keypair
├── send.py / receive.py        # Core sender/receiver pipeline (CLI + importable)
├── streamlit_app.py            # Deployed web demo (Streamlit)
├── app.py                      # Desktop GUI (Tkinter)
├── api_server.py               # FastAPI backend (for the React frontend)
├── frontend/                   # React + Vite frontend (talks to api_server.py)
├── requirements.txt            # Full dependencies (local dev)
├── requirements-deploy.txt     # Lightweight deps for Streamlit Cloud (CPU torch, no Qiskit)
├── .streamlit/config.toml      # Streamlit theme
├── checkpoints/                # Saved model weights (generated during training)
├── keys/                       # Receiver RSA keypair (⚠️ never commit real keys)
├── messages/                   # stego.png + package.json / .qsteg per sent message
└── dataset/                    # DIV2K or other cover/secret image source
⚙️ Setup
bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
🏋️ Training

All hyperparameters live in config.py — edit them there, or override per run:

bash
python -c "from train import train; train(use_encryption=False, epochs=60)"

Resume from a checkpoint — training can be safely stopped and resumed without losing progress:

bash
python -c "from train import train; train(use_encryption=False, epochs=40, resume_from=True)"
🚀 Running the Demo

Option A — Web app (Streamlit):

bash
streamlit run streamlit_app.py

Or just use the hosted version: quantum-gan-stego.streamlit.app

Option B — Desktop app (Tkinter):

bash
python app.py

Option C — Full-stack app (FastAPI + React, live step-by-step progress):

bash
# Terminal 1
pip install fastapi "uvicorn[standard]" python-multipart
uvicorn api_server:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev

Option D — Command line:

bash
python setup_receiver_identity.py
python send.py --cover cover.jpg --secret secret.jpg --receiver-public-key keys/receiver_public_key.pem --out-name message1
python receive.py --message messages/message1.qsteg --receiver-private-key keys/receiver_private_key.pem --out-name message1
📊 Sample Results
Metric	Value
PSNR (Stego Recovery)	20.88 dB
SSIM (Stego Recovery)	0.8362

The Exact Recovery (cryptographic path) is always pixel-perfect once decryption succeeds — the numbers above refer to the neural Approximate Recovery path (raw GAN decoder output).

🗺️ Roadmap
 Train on larger, more diverse datasets (COCO, BOSSBase) to close content-dependent generalization gaps
 Instance Normalization in Encoder/Decoder for better robustness to unfamiliar image content
 Quantization-aware training toward exact neural recovery (not just the parallel cryptographic path)
 Robustness testing: JPEG compression, noise, cropping, resizing
 Migration toward an elliptic-curve-authenticated, ViT-steganalyzed, self-healing extended framework
 Automated hyperparameter/experiment logging per checkpoint
🛠️ Tech Stack

PyTorch · Qiskit · cryptography (RSA/AES) · Streamlit · FastAPI · React (Vite) · Tkinter · scikit-image · NumPy / Pillow

⚠️ Security Note

This is an academic/research project demonstrating the intersection of cryptography and neural steganography. The keys/ folder contains real RSA key material when generated locally — never commit real keys to a public repository.

🙏 Acknowledgements

DIV2K Dataset — high-resolution cover/secret image source · PyTorch, Streamlit, FastAPI, React, and Qiskit open-source communities
