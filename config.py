"""
config.py
---------
ALL tunable settings for the entire project live here, in one place.
When we discuss changing anything later — image size, loss weights,
epochs, dataset path — you change ONE number here instead of hunting
through multiple files.

Import this in every other file:  from config import CFG

PATHS (CHANGED for VS Code / local use): the old paths were hardcoded to
"/content/..." -- that's Colab's project root and doesn't exist on a
normal machine. They're now built from BASE_DIR, the folder this
config.py file itself lives in, so everything (checkpoints/, keys/,
messages/, results/, dataset/) gets created right next to your project
files no matter where you clone/run it from -- no path editing needed
when moving between Colab and VS Code (or anyone else's machine).
"""

import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Config:
    # ---------------- Image / Data ----------------
    IMAGE_SIZE: int = 128          
    BATCH_SIZE: int = 8
    USE_SYNTHETIC_DATA: bool = True   
    DATASET_FOLDER: str = os.path.join(BASE_DIR, "dataset", "DIV2K_valid_HR")  

    # ---------------- Training ----------------
    EPOCHS: int = 60               
    LR_ENCODER_DECODER: float = 1e-3

    LR_DISCRIMINATOR: float = 5e-5


    ALPHA_RECONSTRUCTION: float = 2.0
    BETA_IMAGE_QUALITY: float = 0.75
    GAMMA_ADVERSARIAL: float = 0.005


    PERCEPTUAL_WEIGHT: float = 0.02

    # ---------------- Encoder ----------------

    RESIDUAL_STRENGTH: float = 0.4
    ENCODER_HIDDEN_CHANNELS: int = 64
    DECODER_HIDDEN_CHANNELS: int = 64
    DISCRIMINATOR_HIDDEN_CHANNELS: int = 16

    

    # ---------------- Security Layer ----------------
    USE_ENCRYPTION: bool = True     
    USE_KEY_EXCHANGE: bool = True   
    AES_KEY_BYTES: int = 16         
    RSA_KEY_SIZE: int = 2048

    SECRET_DOWNSCALE_FACTOR: float = 0.125

    USE_REED_SOLOMON: bool = True
    RS_NSYM: int = 100      
    RS_REDUNDANCY: int = 16
                              

    # ---------------- Robustness Testing ----------------
    TEST_JPEG_QUALITY: int = 75     
    TEST_GAUSSIAN_NOISE_STD: float = 0.02  
    TEST_RESIZE_FACTOR: float = 0.9         

    # ---------------- Paths ----------------
    
    CHECKPOINT_DIR: str = os.path.join(BASE_DIR, "checkpoints")
    RESULTS_DIR: str = os.path.join(BASE_DIR, "results")

    # ---------------- Real Sender/Receiver Demo ----------------

    KEYS_DIR: str = os.path.join(BASE_DIR, "keys")          
    MESSAGES_DIR: str = os.path.join(BASE_DIR, "messages")  


CFG = Config()