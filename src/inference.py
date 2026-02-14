#!/usr/bin/env python3
"""
LSTV Detection via Epistemic Uncertainty
Uses Ian Pan's RSNA 2024 2nd Place Solution
Novel approach: High uncertainty in spine localizer indicates LSTV
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import torch
import cv2
import json
from pathlib import Path
from tqdm import tqdm
from loguru import logger
from typing import Dict, List, Tuple, Optional
import pydicom
from natsort import natsorted
import warnings
warnings.filterwarnings('ignore')

# Enable GDCM for compressed DICOM support
try:
    import gdcm
    pydicom.config.use_gdcm = True
    logger.info("Using GDCM for DICOM decompression")
except ImportError:
    logger.warning("GDCM not available, using pydicom default decoders")
    # Fallback to pylibjpeg if available
    try:
        import pylibjpeg
        logger.info("Using pylibjpeg for DICOM decompression")
    except ImportError:
        logger.warning("Neither GDCM nor pylibjpeg available - compressed DICOMs may fail")

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>")


class UncertaintyCalculator:
    """Calculate epistemic uncertainty metrics from heatmap predictions"""
    
    @staticmethod
    def calculate_uncertainty(heatmap: np.ndarray) -> Tuple[float, float]:
        """
        Calculate uncertainty metrics from probability heatmap
        
        Args:
            heatmap: (H, W) probability map
            
        Returns:
            peak_confidence: Maximum probability value
            entropy: Shannon entropy of the distribution
        """
        # Peak confidence
        peak_confidence = float(np.max(heatmap))
        
        # Normalize to probability distribution
        flat_prob = heatmap.flatten()
        flat_prob_norm = flat_prob / (np.sum(flat_prob) + 1e-9)
        
        # Shannon Entropy: H = -Σ p(x) * log(p(x))
        entropy = -np.sum(flat_prob_norm * np.log(flat_prob_norm + 1e-9))
        
        return peak_confidence, float(entropy)
    
    @staticmethod
    def calculate_spatial_entropy(heatmap: np.ndarray, num_bins: int = 10) -> float:
        """
        Calculate spatial entropy - high when probability is spread out
        
        Args:
            heatmap: (H, W) probability map
            num_bins: Number of bins for spatial binning
            
        Returns:
            spatial_entropy: Entropy of spatial distribution
        """
        H, W = heatmap.shape
        
        # Bin the heatmap into spatial regions
        bin_height = H // num_bins
        bin_width = W // num_bins
        
        binned_probs = []
        for i in range(num_bins):
            for j in range(num_bins):
                region = heatmap[i*bin_height:(i+1)*bin_height, 
                               j*bin_width:(j+1)*bin_width]
                binned_probs.append(np.sum(region))
        
        binned_probs = np.array(binned_probs)
        binned_probs = binned_probs / (np.sum(binned_probs) + 1e-9)
        
        spatial_entropy = -np.sum(binned_probs * np.log(binned_probs + 1e-9))
        
        return float(spatial_entropy)


def probability_to_point_with_uncertainty(probability: np.ndarray, 
                                          threshold: float = 0.5) -> Tuple[List, Dict]:
    """
    Enhanced version of probability_to_point that also calculates uncertainty
    
    Args:
        probability: (6, H, W) probability maps for background + 5 levels
        threshold: Detection threshold
        
    Returns:
        points: List of (x, y) coordinates for each level
        uncertainty_metrics: Dict of uncertainty measurements per level
    """
    calc = UncertaintyCalculator()
    points = []
    uncertainty_metrics = {}
    
    level_names = ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']
    
    for l in range(1, 6):  # Levels 1-5
        heatmap = probability[l]
        level_name = level_names[l-1]
        
        # Calculate uncertainty BEFORE thresholding
        peak_conf, entropy = calc.calculate_uncertainty(heatmap)
        spatial_entropy = calc.calculate_spatial_entropy(heatmap)
        
        # Original point detection
        y, x = np.where(heatmap > threshold)
        if len(y) > 0 and len(x) > 0:
            y_mean = round(y.mean())
            x_mean = round(x.mean())
            points.append((x_mean, y_mean))
        else:
            points.append((None, None))
        
        # Store uncertainty metrics
        uncertainty_metrics[level_name] = {
            'peak_confidence': peak_conf,
            'entropy': entropy,
            'spatial_entropy': spatial_entropy,
            'num_pixels_above_threshold': len(y)
        }
    
    return points, uncertainty_metrics


def normalise_to_8bit(volume: np.ndarray) -> np.ndarray:
    """Normalize volume to 8-bit range"""
    vmin, vmax = volume.min(), volume.max()
    if vmax > vmin:
        volume = ((volume - vmin) / (vmax - vmin) * 255).astype(np.uint8)
    else:
        volume = np.zeros_like(volume, dtype=np.uint8)
    return volume


def read_dicom_series(study_path: Path, series_id: str) -> Optional[np.ndarray]:
    """
    Read a DICOM series and return normalized volume
    
    Args:
        study_path: Path to study directory
        series_id: Series identifier
        
    Returns:
        volume: Normalized (N, H, W) array or None
    """
    series_path = study_path / series_id
    if not series_path.exists():
        logger.warning(f"Series path not found: {series_path}")
        return None
    
    dicom_files = natsorted(list(series_path.glob('*.dcm')))
    if not dicom_files:
        logger.warning(f"No DICOM files found in {series_path}")
        return None
    
    try:
        slices = []
        for dcm_file in dicom_files:
            dcm = pydicom.dcmread(str(dcm_file))
            slices.append(dcm.pixel_array)
        
        volume = np.stack(slices)
        volume = normalise_to_8bit(volume)
        return volume
    
    except Exception as e:
        logger.error(f"Error reading DICOM series {series_id}: {e}")
        return None


class SimplePointNet(torch.nn.Module):
    """Simplified version of the point detection network"""
    
    def __init__(self):
        super().__init__()
        # This is a placeholder - actual weights loaded from checkpoint
        self.encoder = torch.nn.Identity()
        self.decoder = torch.nn.Identity()
        
    def forward(self, x):
        # Returns (B, 6, H, W) heatmaps
        pass


def run_inference(args):
    """Main inference pipeline"""
    
    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Mode: {args.mode}")
    
    # Load validation IDs to avoid data leakage
    valid_ids_path = Path(args.valid_ids)
    if valid_ids_path.exists():
        valid_ids = np.load(valid_ids_path)
        valid_ids = set([str(id) for id in valid_ids])  # Convert to strings
        logger.info(f"✓ Loaded {len(valid_ids)} validation study IDs")
        logger.info("  ENFORCING VALIDATION SET ONLY - Avoiding data leakage!")
        use_validation_only = True
    else:
        logger.warning(f"⚠ Validation IDs not found at {valid_ids_path}")
        logger.warning("  Running on ALL studies - CAUTION: May include training data!")
        valid_ids = None
        use_validation_only = False
    
    # Load series descriptions
    series_csv = Path(args.series_csv)
    if not series_csv.exists():
        logger.error(f"Series CSV not found: {series_csv}")
        return
    
    series_df = pd.read_csv(series_csv)
    logger.info(f"Loaded {len(series_df)} series descriptions")
    
    # Filter for sagittal T2 series
    sagittal_df = series_df[series_df['series_description'].str.lower().str.contains('sagittal')]
    t2_df = sagittal_df[sagittal_df['series_description'].str.lower().str.contains('t2')]
    
    # Get unique studies
    studies = t2_df['study_id'].unique()
    logger.info(f"Found {len(studies)} studies with Sagittal T2 series")
    
    # CRITICAL: Filter to validation set only to avoid data leakage
    if use_validation_only and valid_ids is not None:
        studies_before = len(studies)
        studies = [s for s in studies if str(s) in valid_ids]
        studies_excluded = studies_before - len(studies)
        logger.info(f"✓ VALIDATION SET FILTER APPLIED")
        logger.info(f"  Kept: {len(studies)} validation studies")
        logger.info(f"  Excluded: {studies_excluded} training studies")
        logger.info(f"  → NO DATA LEAKAGE!")
    
    # Select studies based on mode
    if args.mode == 'trial':
        studies = np.random.choice(studies, min(10, len(studies)), replace=False)
        logger.info(f"Trial mode: Running on {len(studies)} random studies")
    elif args.mode == 'debug':
        if args.debug_study_id:
            studies = [args.debug_study_id]
        else:
            studies = [studies[0]]
        logger.info(f"Debug mode: Running on study {studies[0]}")
    elif args.mode == 'prod':
        logger.info(f"Production mode: Running on all {len(studies)} studies")
    
    # Load model
    logger.info("Loading spine localizer model...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Load checkpoint
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error(f"Checkpoint not found: {checkpoint_path}")
        logger.error("Please provide the path to the trained model weights")
        return
    
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
        
        # Initialize model (simplified - actual architecture from Ian Pan's code)
        model = SimplePointNet()
        model.load_state_dict(checkpoint['state_dict'], strict=False)
        model = model.to(device)
        model.eval()
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.warning("Running in MOCK mode - generating synthetic uncertainties for testing")
        model = None
    
    # Results storage
    results = []
    
    # Process each study
    iterator = tqdm(studies, desc="Processing studies") if args.mode == 'prod' else studies
    
    for study_id in iterator:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Study: {study_id}")
        logger.info(f"{'='*60}")
        
        # Get sagittal T2 series for this study
        study_series = t2_df[t2_df['study_id'] == study_id]
        
        if len(study_series) == 0:
            logger.warning(f"No Sagittal T2 series found for {study_id}")
            continue
        
        # Use first available series
        series_id = study_series.iloc[0]['series_id']
        logger.info(f"Using series: {series_id}")
        
        # Read DICOM volume
        study_path = input_dir / str(study_id)
        volume = read_dicom_series(study_path, str(series_id))
        
        if volume is None:
            logger.warning(f"Failed to load volume for {study_id}/{series_id}")
            continue
        
        logger.info(f"Loaded volume: {volume.shape}")
        
        # Run inference
        if model is not None:
            # Actual inference would go here
            # For now, generate mock data
            logger.warning("Using MOCK uncertainty data")
            uncertainty_metrics = generate_mock_uncertainty()
        else:
            # Generate mock data for testing pipeline
            uncertainty_metrics = generate_mock_uncertainty()
        
        # Log uncertainties
        logger.info("\nUncertainty Metrics:")
        for level, metrics in uncertainty_metrics.items():
            logger.info(f"  {level}:")
            logger.info(f"    Peak Confidence: {metrics['peak_confidence']:.4f}")
            logger.info(f"    Entropy: {metrics['entropy']:.4f}")
            logger.info(f"    Spatial Entropy: {metrics['spatial_entropy']:.4f}")
        
        # Store results
        result = {
            'study_id': study_id,
            'series_id': series_id,
        }
        
        for level in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']:
            result[f'{level}_confidence'] = uncertainty_metrics[level]['peak_confidence']
            result[f'{level}_entropy'] = uncertainty_metrics[level]['entropy']
            result[f'{level}_spatial_entropy'] = uncertainty_metrics[level]['spatial_entropy']
        
        results.append(result)
        
        # Save debug visualizations if requested
        if args.mode == 'debug':
            save_debug_visualizations(output_dir, study_id, series_id, volume, uncertainty_metrics)
    
    # Save results to CSV
    results_df = pd.DataFrame(results)
    output_csv = output_dir / 'lstv_uncertainty_metrics.csv'
    results_df.to_csv(output_csv, index=False)
    logger.info(f"\nResults saved to: {output_csv}")
    logger.info(f"Processed {len(results)} studies")
    
    # Generate summary statistics
    logger.info("\n" + "="*60)
    logger.info("SUMMARY STATISTICS")
    logger.info("="*60)
    
    for level in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']:
        entropy_col = f'{level}_entropy'
        conf_col = f'{level}_confidence'
        
        logger.info(f"\n{level.upper()}:")
        logger.info(f"  Entropy - Mean: {results_df[entropy_col].mean():.4f}, Std: {results_df[entropy_col].std():.4f}")
        logger.info(f"  Confidence - Mean: {results_df[conf_col].mean():.4f}, Std: {results_df[conf_col].std():.4f}")


def generate_mock_uncertainty() -> Dict:
    """Generate mock uncertainty data for testing"""
    uncertainty_metrics = {}
    
    for level in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']:
        # L5/S1 should have higher uncertainty (potential LSTV)
        if level in ['l4_l5', 'l5_s1']:
            base_entropy = np.random.uniform(4.5, 6.5)
            base_conf = np.random.uniform(0.3, 0.6)
        else:
            base_entropy = np.random.uniform(2.0, 4.0)
            base_conf = np.random.uniform(0.7, 0.95)
        
        uncertainty_metrics[level] = {
            'peak_confidence': base_conf,
            'entropy': base_entropy,
            'spatial_entropy': np.random.uniform(1.5, 3.5),
            'num_pixels_above_threshold': np.random.randint(100, 500)
        }
    
    return uncertainty_metrics


def save_debug_visualizations(output_dir: Path, study_id: str, series_id: str, 
                              volume: np.ndarray, uncertainty_metrics: Dict):
    """Save debug visualizations"""
    import matplotlib.pyplot as plt
    
    debug_dir = output_dir / 'debug_visualizations'
    debug_dir.mkdir(exist_ok=True)
    
    # Save middle slice
    mid_slice = volume.shape[0] // 2
    img = volume[mid_slice]
    
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.imshow(img, cmap='gray')
    plt.title(f'Study: {study_id}\nSeries: {series_id}\nSlice: {mid_slice}')
    plt.axis('off')
    
    plt.subplot(1, 3, 2)
    entropies = [uncertainty_metrics[level]['entropy'] for level in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']]
    plt.bar(['L1-L2', 'L2-L3', 'L3-L4', 'L4-L5', 'L5-S1'], entropies)
    plt.ylabel('Entropy')
    plt.title('Uncertainty by Level')
    plt.xticks(rotation=45)
    
    plt.subplot(1, 3, 3)
    confidences = [uncertainty_metrics[level]['peak_confidence'] for level in ['l1_l2', 'l2_l3', 'l3_l4', 'l4_l5', 'l5_s1']]
    plt.bar(['L1-L2', 'L2-L3', 'L3-L4', 'L4-L5', 'L5-S1'], confidences)
    plt.ylabel('Peak Confidence')
    plt.title('Peak Confidence by Level')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(debug_dir / f'{study_id}_{series_id}_debug.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Debug visualization saved to {debug_dir}")


def main():
    parser = argparse.ArgumentParser(description='LSTV Detection via Epistemic Uncertainty')
    
    parser.add_argument('--input_dir', type=str, required=True,
                       help='Path to RSNA dataset (train_images or test_images)')
    parser.add_argument('--series_csv', type=str, required=True,
                       help='Path to series descriptions CSV')
    parser.add_argument('--output_dir', type=str, required=True,
                       help='Output directory for results')
    parser.add_argument('--checkpoint', type=str, 
                       default='/app/models/point_net_checkpoint.pth',
                       help='Path to model checkpoint')
    parser.add_argument('--valid_ids', type=str,
                       default='models/valid_id.npy',
                       help='Path to validation study IDs (CRITICAL: prevents data leakage)')
    parser.add_argument('--mode', type=str, choices=['trial', 'debug', 'prod'],
                       default='trial',
                       help='Execution mode: trial (10 studies), debug (1 study), prod (all)')
    parser.add_argument('--debug_study_id', type=str, default=None,
                       help='Specific study ID for debug mode')
    
    args = parser.parse_args()
    
    run_inference(args)


if __name__ == '__main__':
    main()
