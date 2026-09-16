"""
models.py
---------
U-Net Encoder (skip connections) + deeper residual-block Decoder +
CNN Discriminator. See project notes: the original shallow 4-layer version
plateaued badly on full image-in-image hiding; this version fixed that for
the non-encrypted case (SSIM 0.78) and substantially improved the encrypted
case too.
"""

import torch
import torch.nn as nn
from config import CFG


def conv_block(in_ch, out_ch, k=3, s=1, p=1):
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, kernel_size=k, stride=s, padding=p),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(inplace=True),
    )


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        return self.relu(out + residual)


class Encoder(nn.Module):
    def __init__(self, hidden_channels: int = None):
        super().__init__()
        base = CFG.ENCODER_HIDDEN_CHANNELS if hidden_channels is None else hidden_channels

        self.enc1 = conv_block(6, base)
        self.enc2 = conv_block(base, base * 2, k=4, s=2, p=1)
        self.enc3 = conv_block(base * 2, base * 4, k=4, s=2, p=1)

        self.bottleneck = nn.Sequential(ResidualBlock(base * 4), ResidualBlock(base * 4))

        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, kernel_size=4, stride=2, padding=1)
        self.dec2 = conv_block(base * 4, base * 2)

        self.up1 = nn.ConvTranspose2d(base * 2, base, kernel_size=4, stride=2, padding=1)
        self.dec1 = conv_block(base * 2, base)

        self.final = nn.Sequential(nn.Conv2d(base, 3, kernel_size=3, padding=1), nn.Tanh())
        self.residual_strength = CFG.RESIDUAL_STRENGTH

    def forward(self, cover, secret):
        x = torch.cat([cover, secret], dim=1)
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        b = self.bottleneck(e3)
        d2 = self.up2(b)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        residual = self.final(d1)
        stego = cover + self.residual_strength * residual
        return torch.clamp(stego, -1.0, 1.0)


class Decoder(nn.Module):
    def __init__(self, hidden_channels: int = None):
        super().__init__()
        base = CFG.DECODER_HIDDEN_CHANNELS if hidden_channels is None else hidden_channels

        self.stem = conv_block(3, base)
        self.down = conv_block(base, base * 2, k=4, s=2, p=1)
        self.res_blocks = nn.Sequential(ResidualBlock(base * 2), ResidualBlock(base * 2), ResidualBlock(base * 2))
        self.up = nn.ConvTranspose2d(base * 2, base, kernel_size=4, stride=2, padding=1)
        self.refine = conv_block(base, base)
        self.final = nn.Sequential(nn.Conv2d(base, 3, kernel_size=3, padding=1), nn.Tanh())

    def forward(self, stego):
        x = self.stem(stego)
        x = self.down(x)
        x = self.res_blocks(x)
        x = self.up(x)
        x = self.refine(x)
        return self.final(x)


class Discriminator(nn.Module):
    def __init__(self, hidden_channels: int = None):
        base = CFG.DISCRIMINATOR_HIDDEN_CHANNELS if hidden_channels is None else hidden_channels
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, base, kernel_size=4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(base, base * 2, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(base * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(base * 2, base * 4, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(base * 4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(base * 4, 1),
            nn.Sigmoid(),
        )

    def forward(self, image):
        return self.net(image)


if __name__ == "__main__":
    B, H, W = 4, 128, 128
    cover = torch.randn(B, 3, H, W)
    secret = torch.randn(B, 3, H, W)
    encoder, decoder, discriminator = Encoder(), Decoder(), Discriminator()
    stego = encoder(cover, secret)
    decoded = decoder(stego)
    pred = discriminator(stego)
    assert stego.shape == cover.shape
    assert decoded.shape == secret.shape
    print("All shape checks passed.")
