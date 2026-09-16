"""
dataset.py
----------
Two dataset options: synthetic (smoke test, no download) and a real image
folder (recommended: DIV2K validation set, ~450MB).
"""

import os
import glob
import random
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image, ImageEnhance


class SyntheticSteganoDataset(Dataset):
    def __init__(self, num_samples: int = 200, image_size: int = 128):
        self.num_samples = num_samples
        self.image_size = image_size

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        cover = torch.rand(3, self.image_size, self.image_size) * 2 - 1
        secret = torch.rand(3, self.image_size, self.image_size) * 2 - 1
        return cover, secret


class FolderSteganoDataset(Dataset):
    def __init__(self, folder_path: str, image_size: int = 128, augment: bool = True):
        self.paths = sorted(
            glob.glob(os.path.join(folder_path, "*.jpg")) +
            glob.glob(os.path.join(folder_path, "*.jpeg")) +
            glob.glob(os.path.join(folder_path, "*.png"))
        )
        assert len(self.paths) >= 2, f"Need at least 2 images in {folder_path}, found {len(self.paths)}"
        self.image_size = image_size
        self.augment = augment

    def __len__(self):
        return len(self.paths)

    def _load(self, path):
        img = Image.open(path).convert("RGB")


        w, h = img.size
        if w != h:
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        if self.augment:


            # 1) Random-crop-from-a-slightly-larger-square, instead of
            # always the same center crop -- adds translation variety.
            oversize = int(side * 1.15)
            img_padded = img.resize((oversize, oversize))
            max_off = oversize - side
            ox, oy = random.randint(0, max_off), random.randint(0, max_off)
            img = img_padded.crop((ox, oy, ox + side, oy + side))

            # 2) Random horizontal flip.
            if random.random() < 0.5:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)

         
            for enhancer_cls in (ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Color):
                factor = random.uniform(0.85, 1.15)
                img = enhancer_cls(img).enhance(factor)

        img = img.resize((self.image_size, self.image_size))
        arr = np.array(img).astype(np.float32) / 127.5 - 1.0
        return torch.from_numpy(arr).permute(2, 0, 1)

    def __getitem__(self, idx):
        cover_path = self.paths[idx]
        secret_path = self.paths[(idx + 1) % len(self.paths)]
        return self._load(cover_path), self._load(secret_path)


def get_dataloader(use_synthetic=None, folder_path=None, batch_size=None, image_size=None, augment=True):
    from config import CFG
    use_synthetic = CFG.USE_SYNTHETIC_DATA if use_synthetic is None else use_synthetic
    folder_path = CFG.DATASET_FOLDER if folder_path is None else folder_path
    batch_size = CFG.BATCH_SIZE if batch_size is None else batch_size
    image_size = CFG.IMAGE_SIZE if image_size is None else image_size

    if use_synthetic:
        dataset = SyntheticSteganoDataset(num_samples=200, image_size=image_size)
    else:
        dataset = FolderSteganoDataset(folder_path, image_size=image_size, augment=augment)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)