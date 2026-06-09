#!/usr/bin/env python3
"""
UAV-specific Data Augmentation for YOLOv4-tiny Wildfire Detection.

Designed for aerial/thermal imagery from UAV-based forest fire patrol missions.
Enhances training data robustness against:
- Varying flight altitudes (scale changes)
- Camera tilt and vibration (rotation, blur)
- Atmospheric haze (fog, smoke simulation)
- Time-of-day lighting variations (brightness, contrast)
- Partial occlusion by tree canopy

Usage:
    from uav_augment import UAVAugmenter
    augmenter = UAVAugmenter(img_size=416)
    augmented = augmenter(image, bboxes)
    
    # Or use as Albumentations transform in YOLOv8 training:
    # python train.py --augment-config uav_augment.yaml
"""

import random
import math
import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    import albumentations as A
    from albumentations.core.transforms_interface import ImageOnlyTransform
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    print("Warning: albumentations not installed. Install with: pip install albumentations")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: opencv not installed. Install with: pip install opencv-python")


class SmokeHazeTransform(ImageOnlyTransform):
    """Simulate atmospheric smoke and haze from wildfire.
    
    Adds semi-transparent gray/white overlay with spatial variation,
    mimicking real smoke conditions encountered during UAV fire patrol.
    
    Args:
        intensity_range: (min, max) haze intensity [0, 1]
        smoke_color: RGB tuple for smoke color (default: light gray)
        spatial_variation: Enable spatially varying smoke density
        p: Probability of applying this transform
    """
    
    def __init__(
        self,
        intensity_range: Tuple[float, float] = (0.05, 0.3),
        smoke_color: Tuple[int, int, int] = (200, 200, 200),
        spatial_variation: bool = True,
        always_apply: bool = False,
        p: float = 0.5,
    ):
        super().__init__(always_apply=always_apply, p=p)
        self.intensity_range = intensity_range
        self.smoke_color = smoke_color
        self.spatial_variation = spatial_variation
    
    def apply(self, img: np.ndarray, **params) -> np.ndarray:
        if not CV2_AVAILABLE:
            return img
        
        h, w = img.shape[:2]
        intensity = random.uniform(*self.intensity_range)
        
        if self.spatial_variation:
            # Create spatially varying smoke mask using Perlin-like noise
            smoke_mask = self._generate_smoke_mask(h, w, intensity)
        else:
            smoke_mask = np.full((h, w), intensity, dtype=np.float32)
        
        # Blend smoke with original image
        smoke_overlay = np.full_like(img, self.smoke_color, dtype=np.float32)
        smoke_mask_3d = smoke_mask[:, :, np.newaxis]
        result = img * (1 - smoke_mask_3d) + smoke_overlay * smoke_mask_3d
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _generate_smoke_mask(self, h: int, w: int, max_intensity: float) -> np.ndarray:
        """Generate spatially varying smoke density mask."""
        # Use multiple octaves of random noise for natural-looking smoke
        mask = np.zeros((h, w), dtype=np.float32)
        
        for octave in range(3):
            scale = 2 ** octave
            small_h = max(h // scale, 2)
            small_w = max(w // scale, 2)
            noise = np.random.rand(small_h, small_w).astype(np.float32)
            
            if CV2_AVAILABLE:
                noise = cv2.resize(noise, (w, h), interpolation=cv2.INTER_LINEAR)
            else:
                # Fallback: simple repeat
                noise = np.repeat(np.repeat(noise, scale, axis=0), scale, axis=1)[:h, :w]
            
            mask += noise * (max_intensity / (octave + 1))
        
        mask = np.clip(mask, 0, max_intensity)
        return mask
    
    def get_transform_init_args_names(self):
        return ("intensity_range", "smoke_color", "spatial_variation")


class ThermalDriftTransform(ImageOnlyTransform):
    """Simulate thermal camera sensor drift and noise.
    
    Mimics artifacts from thermal imaging sensors used in
    nighttime UAV fire detection patrols.
    
    Args:
        drift_intensity: Magnitude of thermal drift [0, 1]
        noise_std: Standard deviation of thermal noise
        p: Probability of applying this transform
    """
    
    def __init__(
        self,
        drift_intensity: float = 0.1,
        noise_std: float = 5.0,
        always_apply: bool = False,
        p: float = 0.3,
    ):
        super().__init__(always_apply=always_apply, p=p)
        self.drift_intensity = drift_intensity
        self.noise_std = noise_std
    
    def apply(self, img: np.ndarray, **params) -> np.ndarray:
        result = img.astype(np.float32)
        
        # Add thermal drift (slow spatial gradient)
        h, w = img.shape[:2]
        drift_angle = random.uniform(0, 2 * math.pi)
        drift_magnitude = random.uniform(0, self.drift_intensity) * 50
            
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        drift = (x_coords * math.cos(drift_angle) + y_coords * math.sin(drift_angle))
        drift = drift / drift.max() * drift_magnitude
        result += drift[:, :, np.newaxis]
        
        # Add thermal noise
        noise = np.random.normal(0, self.noise_std, img.shape).astype(np.float32)
        result += noise
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def get_transform_init_args_names(self):
        return ("drift_intensity", "noise_std")


class MotionBlurTransform(ImageOnlyTransform):
    """Simulate motion blur from UAV flight vibration and movement.
    
    Directional blur aligned with typical UAV flight patterns
    (horizontal for forward flight, vertical for hover vibration).
    
    Args:
        kernel_size_range: (min, max) blur kernel size
        angle_range: (min, max) blur angle in degrees
        p: Probability of applying this transform
    """
    
    def __init__(
        self,
        kernel_size_range: Tuple[int, int] = (3, 9),
        angle_range: Tuple[float, float] = (-30, 30),
        always_apply: bool = False,
        p: float = 0.4,
    ):
        super().__init__(always_apply=always_apply, p=p)
        self.kernel_size_range = kernel_size_range
        self.angle_range = angle_range
    
    def apply(self, img: np.ndarray, **params) -> np.ndarray:
        if not CV2_AVAILABLE:
            return img
        
        kernel_size = random.randint(*self.kernel_size_range)
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        angle = random.uniform(*self.angle_range)
        
        # Create motion blur kernel
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        mid = kernel_size // 2
        
        # Direction based on angle
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))
        
        for i in range(kernel_size):
            offset = i - mid
            x = int(round(mid + offset * cos_a))
            y = int(round(mid + offset * sin_a))
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] = 1.0
        
        kernel /= kernel.sum() + 1e-6
        
        return cv2.filter2D(img, -1, kernel)
    
    def get_transform_init_args_names(self):
        return ("kernel_size_range", "angle_range")


class UAVPerspectiveTransform(ImageOnlyTransform):
    """Simulate perspective changes from UAV altitude and attitude variations.
    
    Applies random perspective warp to mimic:
    - Altitude changes (zoom in/out)
    - Roll/pitch from wind gusts
    - Yaw from heading changes
    
    Args:
        scale_range: (min, max) scale factor for altitude simulation
        warp_strength: Maximum perspective distortion magnitude
        p: Probability of applying this transform
    """
    
    def __init__(
        self,
        scale_range: Tuple[float, float] = (0.7, 1.3),
        warp_strength: float = 0.05,
        always_apply: bool = False,
        p: float = 0.5,
    ):
        super().__init__(always_apply=always_apply, p=p)
        self.scale_range = scale_range
        self.warp_strength = warp_strength
    
    def apply(self, img: np.ndarray, **params) -> np.ndarray:
        if not CV2_AVAILABLE:
            return img
        
        h, w = img.shape[:2]
        
        # Source corners
        src_pts = np.float32([
            [0, 0], [w, 0], [w, h], [0, h]
        ])
        
        # Destination corners with random perspective distortion
        margin_x = w * self.warp_strength
        margin_y = h * self.warp_strength
        
        dst_pts = np.float32([
            [random.uniform(-margin_x, margin_x), random.uniform(-margin_y, margin_y)],
            [w + random.uniform(-margin_x, margin_x), random.uniform(-margin_y, margin_y)],
            [w + random.uniform(-margin_x, margin_x), h + random.uniform(-margin_y, margin_y)],
            [random.uniform(-margin_x, margin_x), h + random.uniform(-margin_y, margin_y)],
        ])
        
        # Apply scale for altitude simulation
        scale = random.uniform(*self.scale_range)
        center = np.float32([[w/2, h/2]])
        dst_pts = (dst_pts - center) * scale + center
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        result = cv2.warpPerspective(
            img, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101
        )
        
        return result
    
    def get_transform_init_args_names(self):
        return ("scale_range", "warp_strength")


class FireGlowTransform(ImageOnlyTransform):
    """Simulate fire glow illuminating nearby areas.
    
    Adds warm-toned (orange/red) glow around fire regions,
    mimicking real fire illumination effects visible in UAV imagery.
    
    Args:
        glow_intensity: Maximum glow intensity [0, 1]
        glow_radius_range: (min, max) glow radius as fraction of image size
        p: Probability of applying this transform
    """
    
    def __init__(
        self,
        glow_intensity: float = 0.2,
        glow_radius_range: Tuple[float, float] = (0.1, 0.3),
        always_apply: bool = False,
        p: float = 0.4,
    ):
        super().__init__(always_apply=always_apply, p=p)
        self.glow_intensity = glow_intensity
        self.glow_radius_range = glow_radius_range
    
    def apply(self, img: np.ndarray, **params) -> np.ndarray:
        h, w = img.shape[:2]
        
        # Random glow center (biased towards center where fire typically appears)
        cx = int(random.gauss(w/2, w/4))
        cy = int(random.gauss(h/2, h/4))
        cx = max(0, min(w-1, cx))
        cy = max(0, min(h-1, cy))
        
        # Random glow radius
        radius = int(random.uniform(*self.glow_radius_range) * min(h, w))
        intensity = random.uniform(0, self.glow_intensity)
        
        # Create radial glow mask
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        dist = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2)
        glow_mask = np.clip(1.0 - dist / radius, 0, 1) ** 2 * intensity
        
        # Fire glow color (warm orange)
        glow_color = np.array([255, 140, 30], dtype=np.float32)  # BGR orange
        glow_3d = glow_mask[:, :, np.newaxis] * glow_color
        
        result = img.astype(np.float32) + glow_3d
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def get_transform_init_args_names(self):
        return ("glow_intensity", "glow_radius_range")


class UAVAugmenter:
    """Complete UAV-specific augmentation pipeline for wildfire detection.
    
    Combines standard YOLO augmentations with UAV-specific transforms
    for robust fire detection from aerial platforms.
    
    Args:
        img_size: Target image size (default: 416 for YOLOv4-tiny)
        mode: 'train' or 'val' (val applies only geometric transforms)
    
    Example:
        >>> augmenter = UAVAugmenter(img_size=416, mode='train')
        >>> result = augmenter(image=img, bboxes=bboxes, class_labels=labels)
        >>> aug_img = result['image']
        >>> aug_bboxes = result['bboxes']
    """
    
    def __init__(
        self,
        img_size: int = 416,
        mode: str = 'train',
    ):
        self.img_size = img_size
        self.mode = mode
        
        if not ALBUMENTATIONS_AVAILABLE:
            raise ImportError("albumentations is required: pip install albumentations")
        
        if mode == 'train':
            self.transform = A.Compose(
                [
                    # === Geometric Transforms ===
                    A.LongestMaxSize(max_size=img_size),
                    A.PadIfNeeded(
                        min_height=img_size, min_width=img_size,
                        border_mode=0, value=(114, 114, 114)
                    ),
                    
                    # === UAV-specific: Perspective & Scale ===
                    UAVPerspectiveTransform(
                        scale_range=(0.7, 1.3),
                        warp_strength=0.05,
                        p=0.5,
                    ),
                    
                    # === Standard Augmentations ===
                    A.HorizontalFlip(p=0.5),
                    A.ColorJitter(
                        brightness=0.3,
                        contrast=0.3,
                        saturation=0.2,
                        hue=0.05,
                        p=0.6,
                    ),
                    
                    # === UAV-specific: Motion Blur ===
                    MotionBlurTransform(
                        kernel_size_range=(3, 7),
                        angle_range=(-30, 30),
                        p=0.3,
                    ),
                    
                    # === UAV-specific: Smoke & Haze ===
                    SmokeHazeTransform(
                        intensity_range=(0.05, 0.25),
                        spatial_variation=True,
                        p=0.4,
                    ),
                    
                    # === UAV-specific: Thermal Noise ===
                    ThermalDriftTransform(
                        drift_intensity=0.08,
                        noise_std=3.0,
                        p=0.2,
                    ),
                    
                    # === UAV-specific: Fire Glow ===
                    FireGlowTransform(
                        glow_intensity=0.15,
                        glow_radius_range=(0.1, 0.25),
                        p=0.3,
                    ),
                    
                    # === Regularization ===
                    A.GaussNoise(
                        var_limit=(5, 20),
                        p=0.2,
                    ),
                    A.Downscale(
                        scale_min=0.7,
                        scale_max=0.9,
                        p=0.2,
                    ),
                    A.ToFloat(max_value=255),
                ],
                bbox_params=A.BboxParams(
                    format='yolo',
                    min_area=64,
                    min_visibility=0.3,
                    label_fields=['class_labels'],
                ),
            )
        else:
            # Validation: only resize
            self.transform = A.Compose(
                [
                    A.LongestMaxSize(max_size=img_size),
                    A.PadIfNeeded(
                        min_height=img_size, min_width=img_size,
                        border_mode=0, value=(114, 114, 114)
                    ),
                    A.ToFloat(max_value=255),
                ],
                bbox_params=A.BboxParams(
                    format='yolo',
                    label_fields=['class_labels'],
                ),
            )
    
    def __call__(self, image: np.ndarray, bboxes: List[List[float]], 
                 class_labels: List[int]) -> Dict:
        """Apply augmentation pipeline.
        
        Args:
            image: Input image (HWC, BGR, uint8)
            bboxes: List of [x_center, y_center, width, height] in YOLO format
            class_labels: List of class IDs for each bbox
        
        Returns:
            Dict with 'image', 'bboxes', 'class_labels'
        """
        return self.transform(
            image=image,
            bboxes=bboxes,
            class_labels=class_labels,
        )


def create_uav_yaml(output_path: str = 'uav_augment.yaml') -> str:
    """Generate YOLOv8-compatible augmentation config file.
    
    Creates a YAML config that can be used with YOLOv8 training:
        yolo train --cfg uav_augment.yaml
    
    Args:
        output_path: Path to write YAML config
    
    Returns:
        Path to generated config file
    """
    yaml_content = """# UAV Wildfire Detection Augmentation Config
# Optimized for YOLOv4-tiny on edge devices (Jetson Nano, PYNQ-Z2)
# Combines standard YOLO augmentations with UAV-specific transforms

# HSV augmentation (UAV lighting variations)
hsv_h: 0.015       # Hue variation (reduced for fire color preservation)
hsv_s: 0.4         # Saturation variation
hsv_v: 0.3         # Value (brightness) variation

# Geometric augmentation
degrees: 15.0       # Rotation (UAV attitude changes)
translate: 0.1      # Translation (camera offset)
scale: 0.3          # Scale (altitude variation 0.7x-1.3x)
shear: 5.0          # Shear (wind-induced tilt)
flipud: 0.1         # Vertical flip (inverted flight rare)
fliplr: 0.5         # Horizontal flip (common in UAV)

# Mosaic & MixUp (enhanced for small fire targets)
mosaic: 1.0         # Mosaic probability
mixup: 0.2          # MixUp probability (helps with smoke occlusion)

# Copy-Paste for rare fire instances
copy_paste: 0.3     # Copy-paste probability (critical for class imbalance)

# Advanced settings
erasing: 0.1        # Random erasing (simulates partial occlusion by trees)
crop_fraction: 0.8  # Minimum crop fraction

# UAV-specific notes:
# - Reduced hue shift to preserve fire color signature (orange/red)
# - Higher scale range for altitude variation
# - Copy-paste enabled for rare fire instances
# - Moderate rotation for wind-induced attitude changes
"""
    
    with open(output_path, 'w') as f:
        f.write(yaml_content)
    
    return output_path


if __name__ == '__main__':
    # Demo: apply augmentations to a sample image
    import sys
    
    print("UAV Data Augmentation Demo")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # Load image from file
        if not CV2_AVAILABLE:
            print("Error: OpenCV required for image loading")
            sys.exit(1)
        
        img_path = sys.argv[1]
        img = cv2.imread(img_path)
        if img is None:
            print(f"Error: Cannot load image {img_path}")
            sys.exit(1)
        
        print(f"Loaded image: {img.shape}")
        
        # Create augmenter
        augmenter = UAVAugmenter(img_size=416, mode='train')
        
        # Demo with dummy bounding boxes
        # In real use, load from YOLO annotation files
        dummy_bboxes = [[0.5, 0.5, 0.2, 0.2]]  # Center of image
        dummy_labels = [0]  # Fire class
        
        # Apply augmentation
        result = augmenter(
            image=img,
            bboxes=dummy_bboxes,
            class_labels=dummy_labels,
        )
        
        print(f"Augmented image: {result['image'].shape}")
        print(f"Augmented bboxes: {result['bboxes']}")
        
        # Save result
        if len(sys.argv) > 2:
            out_path = sys.argv[2]
        else:
            out_path = 'augmented_output.jpg'
        
        aug_img = (result['image'] * 255).astype(np.uint8)
        cv2.imwrite(out_path, aug_img)
        print(f"Saved augmented image to {out_path}")
    else:
        # Generate YAML config
        yaml_path = create_uav_yaml()
        print(f"Generated YOLOv8 augmentation config: {yaml_path}")
        print()
        print("Usage:")
        print("  python uav_augment.py <image_path> [output_path]")
        print("  python uav_augment.py  # Generate YAML config only")
        print()
        print("Custom transforms available:")
        print("  - SmokeHazeTransform: Wildfire smoke simulation")
        print("  - ThermalDriftTransform: Thermal sensor noise")
        print("  - MotionBlurTransform: UAV flight vibration")
        print("  - UAVPerspectiveTransform: Altitude/attitude changes")
        print("  - FireGlowTransform: Fire illumination effect")
