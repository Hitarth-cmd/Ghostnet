"""
Marine Debris Segmentation Model Architecture & Inference Service.

Pairs a Vision Transformer (ViT-Small) backbone with a Simple Feature Pyramid Neck
and a UNet++ Nested Dense Skip Decoder, trained on MARIDA and MADOS Sentinel-2 datasets.

Target Checkpoint: segmentation_best.pth (val mIoU: 71.96% across 11 classes).
"""
from __future__ import annotations

import base64
import io
import logging
import os
from typing import Sequence, Tuple, Dict, Any, Optional, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

logger = logging.getLogger("ghostnet.model_architecture")

# 11 Semantic Classes (MARIDA / MADOS harmonized)
CLASS_NAMES = [
    "Marine Debris",             # 0 - Primary Target
    "Dense Sargassum",          # 1
    "Sparse Sargassum",         # 2
    "Natural Organic Material", # 3
    "Ship",                     # 4
    "Clouds",                   # 5
    "Marine Water",             # 6
    "Sediment-Laden Water",     # 7
    "Foam",                     # 8
    "Turbid Water",             # 9
    "Shallow Water",            # 10
]

# Exact RGB Color Palette for the 11 classes
CLASS_PALETTE = np.array(
    [
        [239, 68, 68],    # 0 Marine Debris: High-visibility Red/Coral for operational clarity
        [220, 38, 38],    # 1 Dense Sargassum: Crimson
        [249, 115, 22],   # 2 Sparse Sargassum: Orange
        [234, 179, 8],    # 3 Natural Organic Material: Yellow
        [34, 197, 94],    # 4 Ship: Bright Green
        [156, 163, 175],  # 5 Clouds: Grey
        [30, 58, 138],    # 6 Marine Water: Deep Navy Blue
        [180, 83, 9],     # 7 Sediment-Laden Water: Brown/Mud
        [217, 70, 239],   # 8 Foam: Magenta/Pink
        [6, 182, 212],    # 9 Turbid Water: Cyan
        [125, 211, 252],  # 10 Shallow Water: Light Sky Blue
    ],
    dtype=np.uint8,
)

# Standard Sentinel-2 L2A Band Order for the 11-channel model
S2_BAND_NAMES = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
# B4 (Red) is idx 3, B3 (Green) is idx 2, B2 (Blue) is idx 1
RGB_BAND_INDICES = {"R": 3, "G": 2, "B": 1}


class LayerNorm2d(nn.Module):
    """
    Channel-wise 2D LayerNorm for (B, C, H, W) tensors.
    Matches SimpleFeaturePyramid neck normalization.
    """
    def __init__(self, channels: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(channels))
        self.bias = nn.Parameter(torch.zeros(channels))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        u = x.mean(1, keepdim=True)
        s = (x - u).pow(2).mean(1, keepdim=True)
        x = (x - u) / torch.sqrt(s + self.eps)
        return self.weight[:, None, None] * x + self.bias[:, None, None]


class Attention(nn.Module):
    def __init__(self, dim: int, num_heads: int = 6):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(dim, dim * 3)
        self.proj = nn.Linear(dim, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, N, C = x.shape
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        out = (attn @ v).transpose(1, 2).reshape(B, N, C)
        return self.proj(out)


class MLP(nn.Module):
    def __init__(self, in_features: int, hidden_features: int):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_features, in_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.act(self.fc1(x)))


class ViTBlock(nn.Module):
    def __init__(self, dim: int = 384, num_heads: int = 6, mlp_ratio: float = 4.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = Attention(dim, num_heads=num_heads)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = MLP(dim, int(dim * mlp_ratio))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.norm1(x))
        x = x + self.mlp(self.norm2(x))
        return x


class PatchEmbed(nn.Module):
    def __init__(self, in_chans: int = 11, embed_dim: int = 384, patch_size: int = 8):
        super().__init__()
        self.proj = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Tuple[int, int]]:
        B, C, H, W = x.shape
        x = self.proj(x)
        h, w = x.shape[2], x.shape[3]
        x = x.flatten(2).transpose(1, 2)
        return x, (h, w)


class ViTEncoder(nn.Module):
    def __init__(self, in_chans: int = 11, embed_dim: int = 384, depth: int = 12, num_heads: int = 6):
        super().__init__()
        self.embed_dim = embed_dim
        self.patch_embed = PatchEmbed(in_chans, embed_dim, patch_size=8)
        self.blocks = nn.ModuleList([ViTBlock(embed_dim, num_heads) for _ in range(depth)])
        self.norm = nn.LayerNorm(embed_dim)

    def forward_full(self, x: torch.Tensor) -> Tuple[torch.Tensor, Tuple[int, int]]:
        x, (h, w) = self.patch_embed(x)
        for blk in self.blocks:
            x = blk(x)
        x = self.norm(x)
        return x, (h, w)


class SimpleFeaturePyramidNeck(nn.Module):
    def __init__(self, in_dim: int = 384, out_dims: Tuple[int, ...] = (64, 128, 256, 512)):
        super().__init__()
        self.pre_norms = nn.ModuleList([nn.LayerNorm(in_dim) for _ in range(4)])
        self.up4 = nn.Sequential(
            nn.ConvTranspose2d(in_dim, 192, kernel_size=2, stride=2),
            LayerNorm2d(192),
            nn.GELU(),
            nn.ConvTranspose2d(192, 96, kernel_size=2, stride=2),
        )
        self.proj2 = nn.Conv2d(96, out_dims[0], kernel_size=1)
        self.up2 = nn.ConvTranspose2d(in_dim, 192, kernel_size=2, stride=2)
        self.proj3 = nn.Conv2d(192, out_dims[1], kernel_size=1)
        self.proj4 = nn.Conv2d(in_dim, out_dims[2], kernel_size=1)
        self.down2 = nn.Conv2d(in_dim, in_dim, kernel_size=2, stride=2)
        self.proj5 = nn.Conv2d(in_dim, out_dims[3], kernel_size=1)

    def forward(self, tokens: torch.Tensor, hw: Tuple[int, int]) -> Tuple[torch.Tensor, ...]:
        h, w = hw
        B, N, C = tokens.shape
        def to_2d(t):
            return t.transpose(1, 2).reshape(B, C, h, w)

        t0 = to_2d(self.pre_norms[0](tokens))
        t1 = to_2d(self.pre_norms[1](tokens))
        t2 = to_2d(self.pre_norms[2](tokens))
        t3 = to_2d(self.pre_norms[3](tokens))

        f0 = self.proj2(self.up4(t0))
        f1 = self.proj3(self.up2(t1))
        f2 = self.proj4(t2)
        f3 = self.proj5(self.down2(t3))
        return (f0, f1, f2, f3)


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNetPlusPlus(nn.Module):
    def __init__(
        self,
        in_channels: Tuple[int, ...] = (64, 128, 256, 512),
        decoder_channels: Tuple[int, ...] = (64, 128, 256, 512),
        num_classes: int = 11,
    ):
        super().__init__()
        self.in_proj = nn.ModuleList([nn.Conv2d(c, dc, kernel_size=1) for c, dc in zip(in_channels, decoder_channels)])
        c0, c1, c2, c3 = decoder_channels
        self.conv0_1 = ConvBlock(c0 + c1, c0)
        self.conv1_1 = ConvBlock(c1 + c2, c1)
        self.conv2_1 = ConvBlock(c2 + c3, c2)
        self.conv0_2 = ConvBlock(c0 * 2 + c1, c0)
        self.conv1_2 = ConvBlock(c1 * 2 + c2, c1)
        self.conv0_3 = ConvBlock(c0 * 3 + c1, c0)
        self.final = nn.Conv2d(c0, num_classes, kernel_size=1)

    def forward(self, features: Tuple[torch.Tensor, ...]) -> torch.Tensor:
        x0_0 = self.in_proj[0](features[0])
        x1_0 = self.in_proj[1](features[1])
        x2_0 = self.in_proj[2](features[2])
        x3_0 = self.in_proj[3](features[3])

        def up(x: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
            return F.interpolate(x, size=target.shape[2:], mode="bilinear", align_corners=False)

        x0_1 = self.conv0_1(torch.cat([x0_0, up(x1_0, x0_0)], dim=1))
        x1_1 = self.conv1_1(torch.cat([x1_0, up(x2_0, x1_0)], dim=1))
        x2_1 = self.conv2_1(torch.cat([x2_0, up(x3_0, x2_0)], dim=1))

        x0_2 = self.conv0_2(torch.cat([x0_0, x0_1, up(x1_1, x0_0)], dim=1))
        x1_2 = self.conv1_2(torch.cat([x1_0, x1_1, up(x2_1, x1_0)], dim=1))

        x0_3 = self.conv0_3(torch.cat([x0_0, x0_1, x0_2, up(x1_2, x0_0)], dim=1))
        return self.final(x0_3)


class MarineSegmentationModel(nn.Module):
    """
    Complete ViT + SimpleFeaturePyramidNeck + UNet++ Marine Debris Segmentation Model.
    """
    def __init__(self, in_chans: int = 11, num_classes: int = 11):
        super().__init__()
        self.encoder = ViTEncoder(in_chans=in_chans, embed_dim=384, depth=12, num_heads=6)
        self.neck = SimpleFeaturePyramidNeck(in_dim=384, out_dims=(64, 128, 256, 512))
        self.decoder = UNetPlusPlus(
            in_channels=(64, 128, 256, 512),
            decoder_channels=(64, 128, 256, 512),
            num_classes=num_classes,
        )
        self.num_classes = num_classes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h_in, w_in = x.shape[2], x.shape[3]
        tokens, hw = self.encoder.forward_full(x)
        feats = self.neck(tokens, hw)
        logits = self.decoder(feats)
        return F.interpolate(logits, size=(h_in, w_in), mode="bilinear", align_corners=False)


# ==============================================================================
# Model Loading & Pre/Post-processing Service
# ==============================================================================

_GLOBAL_MODEL: Optional[MarineSegmentationModel] = None
_MODEL_DEVICE = "cpu"


def get_default_checkpoint_path() -> str:
    """Resolve path to segmentation_best.pth."""
    env_path = os.environ.get("MODEL_CHECKPOINT_PATH", "")
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Try current directory, project root, or parent folders
    candidates = [
        "segmentation_best.pth",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "segmentation_best.pth"),
        os.path.join(os.getcwd(), "segmentation_best.pth"),
        os.path.join(os.getcwd(), "..", "segmentation_best.pth"),
    ]
    for c in candidates:
        abs_c = os.path.abspath(c)
        if os.path.exists(abs_c):
            return abs_c
    return "segmentation_best.pth"


def load_model(checkpoint_path: Optional[str] = None) -> MarineSegmentationModel:
    """Load model with checkpoint weights into memory."""
    global _GLOBAL_MODEL, _MODEL_DEVICE
    if _GLOBAL_MODEL is not None:
        return _GLOBAL_MODEL

    path = checkpoint_path or get_default_checkpoint_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Checkpoint not found at: {path}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _MODEL_DEVICE = str(device)
    logger.info("Loading Marine Debris Segmentation Model on device=%s from %s", device, path)

    model = MarineSegmentationModel(in_chans=11, num_classes=11)
    checkpoint = torch.load(path, map_location=device)
    state_dict = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint

    # Strip any potential module. prefixes
    cleaned_sd = {}
    for k, v in state_dict.items():
        if k.startswith("module."):
            cleaned_sd[k[len("module."):]] = v
        else:
            cleaned_sd[k] = v

    model.load_state_dict(cleaned_sd, strict=True)
    model.to(device)
    model.eval()
    _GLOBAL_MODEL = model
    logger.info("Marine Debris Model loaded successfully! (Best metric: %s)", checkpoint.get("best_metric", "N/A"))
    return _GLOBAL_MODEL


def s2_to_rgb(image_11_bands: np.ndarray) -> np.ndarray:
    """
    Extract True-Color RGB (B4=Red, B3=Green, B2=Blue) from 11-band array
    with 2%-98% percentile contrast stretching.
    image_11_bands: shape (11, H, W)
    Returns: (H, W, 3) uint8 RGB array
    """
    if image_11_bands.ndim == 3 and image_11_bands.shape[0] >= 4:
        r = image_11_bands[RGB_BAND_INDICES["R"]].astype(np.float32)
        g = image_11_bands[RGB_BAND_INDICES["G"]].astype(np.float32)
        b = image_11_bands[RGB_BAND_INDICES["B"]].astype(np.float32)
    elif image_11_bands.ndim == 3 and image_11_bands.shape[0] == 3:
        r = image_11_bands[0].astype(np.float32)
        g = image_11_bands[1].astype(np.float32)
        b = image_11_bands[2].astype(np.float32)
    else:
        # Fallback for single channel
        r = g = b = image_11_bands[0].astype(np.float32)

    rgb = np.stack([r, g, b], axis=-1)

    # 2%-98% percentile stretching per channel
    stretched = np.zeros_like(rgb, dtype=np.uint8)
    for c in range(3):
        ch = rgb[..., c]
        low, high = np.percentile(ch, (2.0, 98.0))
        if high > low:
            norm = np.clip((ch - low) / (high - low), 0.0, 1.0)
        else:
            norm = np.clip(ch, 0.0, 1.0)
        stretched[..., c] = (norm * 255.0).astype(np.uint8)

    return stretched


def mask_to_color_image(mask: np.ndarray) -> np.ndarray:
    """Convert integer mask (H, W) to RGB image using CLASS_PALETTE."""
    h, w = mask.shape
    color_mask = np.zeros((h, w, 3), dtype=np.uint8)
    for cls_id in range(len(CLASS_PALETTE)):
        color_mask[mask == cls_id] = CLASS_PALETTE[cls_id]
    return color_mask


def generate_overlay_image(rgb: np.ndarray, pred_mask: np.ndarray, alpha: float = 0.55) -> np.ndarray:
    """
    Create a composite overlay:
    Keep water/background mostly subtle, and highlight Marine Debris (class 0)
    and Sargassum (classes 1, 2) with glowing vibrant colors.
    """
    color_mask = mask_to_color_image(pred_mask)
    overlay = rgb.copy().astype(np.float32)

    # Where debris or sargassum is detected, blend with high prominence
    target_pixels = (pred_mask == 0) | (pred_mask == 1) | (pred_mask == 2) | (pred_mask == 4)
    overlay[target_pixels] = (1.0 - alpha) * rgb[target_pixels] + alpha * color_mask[target_pixels]

    # For other classes, apply softer blend
    other_pixels = ~target_pixels & (pred_mask < len(CLASS_PALETTE))
    soft_alpha = 0.25
    overlay[other_pixels] = (1.0 - soft_alpha) * rgb[other_pixels] + soft_alpha * color_mask[other_pixels]

    return np.clip(overlay, 0, 255).astype(np.uint8)


def array_to_base64_png(arr: np.ndarray) -> str:
    """Convert (H, W, 3) uint8 array to base64 PNG data URL."""
    img = Image.fromarray(arr)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def preprocess_input(
    raw_array: np.ndarray,
    target_size: Optional[Tuple[int, int]] = None,
) -> Tuple[torch.Tensor, np.ndarray, Tuple[int, int]]:
    """
    Preprocess arbitrary image array into (1, 11, H_pad, W_pad) PyTorch tensor.
    Supports:
      - 11-channel Sentinel-2 reflectance (raw DN or /10000)
      - Standard 3-channel RGB image (synthesizes 11 bands for demo/testing)
      - Single-channel or multi-spectral GeoTIFF
    Returns:
      (tensor, rgb_quicklook, original_shape)
    """
    if raw_array.ndim == 2:
        # (H, W) -> expand to (1, H, W)
        raw_array = raw_array[np.newaxis, ...]

    if raw_array.ndim == 3 and raw_array.shape[2] in (3, 4) and raw_array.shape[0] not in (3, 4, 11):
        # (H, W, C) -> transpose to (C, H, W)
        raw_array = np.transpose(raw_array, (2, 0, 1))

    c, h, w = raw_array.shape
    orig_shape = (h, w)

    # Scale reflectance if in DN format (> 1.0)
    if raw_array.max() > 1.0:
        if raw_array.max() > 255.0:
            # Sentinel-2 DN / 10000
            refl = raw_array.astype(np.float32) / 10000.0
        else:
            # 8-bit image 0..255 -> 0..0.3 typical water reflectance
            refl = (raw_array.astype(np.float32) / 255.0) * 0.35
    else:
        refl = raw_array.astype(np.float32)

    # Synthesize 11 bands if input has fewer channels (e.g. RGB or RGBA)
    if c == 11:
        bands_11 = refl
    elif c >= 3:
        # Input is RGB (bands 0, 1, 2)
        r, g, b = refl[0], refl[1], refl[2]
        # Synthesize 11 bands matching S2 spectral profiles:
        # B1 (Aerosol), B2 (Blue), B3 (Green), B4 (Red), B5, B6, B7 (Red Edge), B8, B8A (NIR), B11, B12 (SWIR)
        bands_11 = np.zeros((11, h, w), dtype=np.float32)
        bands_11[0] = b * 0.95              # B1 Coastal aerosol
        bands_11[1] = b                     # B2 Blue
        bands_11[2] = g                     # B3 Green
        bands_11[3] = r                     # B4 Red
        bands_11[4] = (r + g) * 0.5         # B5 Red Edge 1
        bands_11[5] = (r + g) * 0.55        # B6 Red Edge 2
        bands_11[6] = (r + g) * 0.6         # B7 Red Edge 3
        bands_11[7] = np.maximum(g, r) * 0.8# B8 NIR
        bands_11[8] = np.maximum(g, r) * 0.82# B8A NIR narrow
        bands_11[9] = r * 0.6               # B11 SWIR 1
        bands_11[10] = r * 0.5              # B12 SWIR 2
    else:
        # Replicate 1 channel to 11
        bands_11 = np.repeat(refl[:1], 11, axis=0)

    # Generate true-color quicklook for display
    rgb_display = s2_to_rgb(bands_11)

    # Pad dimensions to multiples of 16 for ViT patch 8 and UNet++ levels
    pad_h = (16 - (h % 16)) % 16
    pad_w = (16 - (w % 16)) % 16

    if pad_h > 0 or pad_w > 0:
        padded_bands = np.pad(bands_11, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
    else:
        padded_bands = bands_11

    tensor = torch.from_numpy(padded_bands).unsqueeze(0).float()
    return tensor, rgb_display, orig_shape


def predict_marine_debris(
    raw_array: np.ndarray,
    pixel_size_meters: float = 10.0,
) -> Dict[str, Any]:
    """
    Run full end-to-end prediction pipeline on an input satellite scene/tile.
    Returns visual overlays, per-class analytics, risk score, and debris metrics.
    """
    model = load_model()
    device = next(model.parameters()).device

    tensor, rgb_quicklook, (orig_h, orig_w) = preprocess_input(raw_array)
    tensor = tensor.to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1)
        preds = torch.argmax(logits, dim=1).squeeze(0).cpu().numpy()
        debris_confidence = probs[:, 0].squeeze(0).cpu().numpy()

    # Crop padding back to original dimensions
    pred_mask = preds[:orig_h, :orig_w]
    debris_conf_map = debris_confidence[:orig_h, :orig_w]
    rgb_display = rgb_quicklook[:orig_h, :orig_w]

    # Analytics calculation
    total_pixels = int(pred_mask.size)
    pixel_area_m2 = float(pixel_size_meters ** 2)

    class_counts: Dict[str, Dict[str, Any]] = {}
    for idx, name in enumerate(CLASS_NAMES):
        count = int(np.sum(pred_mask == idx))
        pct = round((count / total_pixels) * 100.0, 4) if total_pixels > 0 else 0.0
        area_m2 = round(count * pixel_area_m2, 2)
        color_hex = "#{:02x}{:02x}{:02x}".format(*CLASS_PALETTE[idx])
        class_counts[name] = {
            "class_id": idx,
            "name": name,
            "pixel_count": count,
            "percentage": pct,
            "area_m2": area_m2,
            "area_km2": round(area_m2 / 1e6, 6),
            "color": color_hex,
        }

    debris_info = class_counts["Marine Debris"]
    debris_pixels = debris_info["pixel_count"]
    debris_pct = debris_info["percentage"]
    debris_area_m2 = debris_info["area_m2"]
    debris_area_km2 = debris_info["area_km2"]

    sargassum_pixels = class_counts["Dense Sargassum"]["pixel_count"] + class_counts["Sparse Sargassum"]["pixel_count"]
    ship_pixels = class_counts["Ship"]["pixel_count"]

    # Ecological Severity Determination
    if debris_pct > 0.5:
        severity = "CRITICAL"
        action = "Dispatch immediate interception and deploy containment booms."
    elif debris_pct > 0.1:
        severity = "HIGH"
        action = "Notify regional maritime response and verify high-density clusters."
    elif debris_pct > 0.02:
        severity = "MODERATE"
        action = "Log target position in tactical monitoring queue."
    else:
        severity = "LOW"
        action = "Water surface clear / trace litter below operational threshold."

    # Mean confidence for detected debris pixels
    if debris_pixels > 0:
        avg_debris_conf = round(float(np.mean(debris_conf_map[pred_mask == 0])), 4)
    else:
        avg_debris_conf = 0.0

    # Visualizations
    color_mask = mask_to_color_image(pred_mask)
    overlay = generate_overlay_image(rgb_display, pred_mask)

    return {
        "summary": {
            "debris_pixel_count": debris_pixels,
            "debris_area_m2": debris_area_m2,
            "debris_area_km2": debris_area_km2,
            "debris_percentage": debris_pct,
            "debris_mean_confidence": avg_debris_conf,
            "sargassum_pixel_count": sargassum_pixels,
            "ship_pixel_count": ship_pixels,
            "severity_level": severity,
            "recommended_action": action,
            "image_dimensions": {"width": orig_w, "height": orig_h},
            "pixel_resolution_meters": pixel_size_meters,
        },
        "class_breakdown": list(class_counts.values()),
        "visualizations": {
            "rgb_quicklook": array_to_base64_png(rgb_display),
            "segmentation_mask": array_to_base64_png(color_mask),
            "debris_overlay": array_to_base64_png(overlay),
        },
        "raw_mask": pred_mask,
        "debris_confidence_map": debris_conf_map,
    }
