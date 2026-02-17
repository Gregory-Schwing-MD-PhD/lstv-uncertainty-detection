#!/usr/bin/env python3
"""
Extract Validation Set DICOMs for GitHub Upload

This script:
1. Loads valid_id.npy (283 validation study IDs)
2. Loads train_series_descriptions.csv
3. Filters for T2 series (Sagittal and Axial)
4. Copies DICOM files to a new directory structure
5. Generates study_metadata.json for the web app

Usage:
    python extract_validation_dicoms.py
"""

import os
import sys
import numpy as np
import pandas as pd
import shutil
import json
from pathlib import Path
from tqdm import tqdm
from loguru import logger
from natsort import natsorted

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

def count_dcm_files(series_dir: Path) -> int:
    """Count DICOM files in a series directory"""
    if not series_dir.exists():
        return 0
    return len(list(series_dir.glob('*.dcm')))

def rename_dcm_files_sequential(series_dir: Path):
    """Rename DICOM files to sequential numbering: 001.dcm, 002.dcm, etc."""
    if not series_dir.exists():
        return 0
    
    dcm_files = natsorted(list(series_dir.glob('*.dcm')))
    
    for idx, dcm_file in enumerate(dcm_files, start=1):
        new_name = f"{idx:03d}.dcm"
        new_path = series_dir / new_name
        
        # Skip if already correctly named
        if dcm_file.name != new_name:
            dcm_file.rename(new_path)
    
    return len(dcm_files)

def main():
    logger.info("="*80)
    logger.info("EXTRACTING VALIDATION SET DICOMs FOR GITHUB UPLOAD")
    logger.info("="*80)
    
    # Paths - using lstv-annotation-tool as base
    repo_dir = Path("/wsu/home/go/go24/go2432/lstv-annotation-tool")
    
    # Source data from lstv-uncertainty-detection project
    source_base = Path("/wsu/home/go/go24/go2432/lstv-uncertainty-detection")
    valid_ids_path = source_base / "models" / "valid_id.npy"
    series_csv_path = source_base / "data" / "raw" / "train_series_descriptions.csv"
    source_dicom_dir = source_base / "data" / "raw" / "train_images"
    
    # Output directory - directly into lstv-annotation-tool repo structure
    output_dicoms = repo_dir / "data" / "dicoms"
    
    logger.info(f"Source DICOM directory: {source_dicom_dir}")
    logger.info(f"Output directory: {output_dicoms}")
    
    # Create output directory
    output_dicoms.mkdir(parents=True, exist_ok=True)
    
    # Load validation IDs
    logger.info("\n" + "="*80)
    logger.info("LOADING VALIDATION STUDY IDs")
    logger.info("="*80)
    
    if not valid_ids_path.exists():
        logger.error(f"valid_id.npy not found at: {valid_ids_path}")
        sys.exit(1)
    
    valid_ids = np.load(valid_ids_path)
    valid_ids = [int(x) for x in valid_ids]
    logger.info(f"✓ Loaded {len(valid_ids)} validation study IDs")
    
    # Load series descriptions
    logger.info("\n" + "="*80)
    logger.info("LOADING SERIES DESCRIPTIONS")
    logger.info("="*80)
    
    if not series_csv_path.exists():
        logger.error(f"Series CSV not found at: {series_csv_path}")
        sys.exit(1)
    
    series_df = pd.read_csv(series_csv_path)
    logger.info(f"✓ Loaded {len(series_df)} total series")
    
    # Filter for T2 series only (Sagittal and Axial)
    t2_df = series_df[series_df['series_description'].str.contains('T2', case=False, na=False)]
    logger.info(f"✓ Filtered to {len(t2_df)} T2 series")
    
    # Filter for validation set only
    t2_df = t2_df[t2_df['study_id'].isin(valid_ids)]
    logger.info(f"✓ Filtered to {len(t2_df)} T2 series in validation set")
    
    # Get unique studies
    validation_studies = t2_df['study_id'].unique()
    logger.info(f"✓ Found {len(validation_studies)} validation studies with T2 series")
    
    # Build metadata structure
    logger.info("\n" + "="*80)
    logger.info("COPYING DICOM FILES AND BUILDING METADATA")
    logger.info("="*80)
    
    studies_metadata = {}
    total_files_copied = 0
    total_bytes_copied = 0
    skipped_studies = []
    
    for study_id in tqdm(validation_studies, desc="Processing studies"):
        study_series = t2_df[t2_df['study_id'] == study_id]
        
        source_study_dir = source_dicom_dir / str(study_id)
        if not source_study_dir.exists():
            logger.warning(f"Source study directory not found: {source_study_dir}")
            skipped_studies.append(study_id)
            continue
        
        # Create output study directory
        output_study_dir = output_dicoms / str(study_id)
        output_study_dir.mkdir(exist_ok=True)
        
        series_list = []
        
        for _, row in study_series.iterrows():
            series_id = row['series_id']
            series_desc = row['series_description']
            
            source_series_dir = source_study_dir / str(series_id)
            
            if not source_series_dir.exists():
                logger.debug(f"Series directory not found: {source_series_dir}")
                continue
            
            # Count files before copying
            num_files = count_dcm_files(source_series_dir)
            
            if num_files == 0:
                logger.debug(f"No DICOM files in series: {series_id}")
                continue
            
            # Create output series directory
            output_series_dir = output_study_dir / str(series_id)
            output_series_dir.mkdir(exist_ok=True)
            
            # Copy all DICOM files
            dcm_files = list(source_series_dir.glob('*.dcm'))
            for dcm_file in dcm_files:
                output_dcm_path = output_series_dir / dcm_file.name
                shutil.copy2(dcm_file, output_dcm_path)
                total_bytes_copied += dcm_file.stat().st_size
            
            total_files_copied += len(dcm_files)
            
            # Rename to sequential numbering
            rename_dcm_files_sequential(output_series_dir)
            
            # Add to metadata
            series_list.append({
                'series_id': int(series_id),
                'series_description': series_desc,
                'num_slices': num_files
            })
        
        if series_list:
            studies_metadata[str(study_id)] = {
                'study_id': int(study_id),
                'series': series_list
            }
    
    # Create final metadata structure
    metadata = {
        'valid_study_ids': [int(sid) for sid in studies_metadata.keys()],
        'studies': studies_metadata
    }
    
    # Save metadata JSON - directly in lstv-annotation-tool repo
    metadata_path = repo_dir / "data" / "study_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("EXTRACTION COMPLETE")
    logger.info("="*80)
    logger.info(f"✓ Processed {len(validation_studies)} validation studies")
    logger.info(f"✓ Successfully extracted {len(studies_metadata)} studies with DICOMs")
    logger.info(f"✓ Skipped {len(skipped_studies)} studies (no source data)")
    logger.info(f"✓ Total DICOM files copied: {total_files_copied:,}")
    logger.info(f"✓ Total data copied: {total_bytes_copied / (1024**3):.2f} GB")
    logger.info(f"✓ Output directory: {output_dicoms}")
    logger.info(f"✓ Metadata saved: {metadata_path}")
    logger.info(f"✓ Ready for Git commit from: {repo_dir}")
    
    # Statistics
    logger.info("\n" + "="*80)
    logger.info("STATISTICS")
    logger.info("="*80)
    
    total_series = sum(len(s['series']) for s in studies_metadata.values())
    logger.info(f"Total studies: {len(studies_metadata)}")
    logger.info(f"Total series: {total_series}")
    logger.info(f"Average series per study: {total_series / len(studies_metadata):.1f}")
    
    series_types = {}
    for study_data in studies_metadata.values():
        for series in study_data['series']:
            desc = series['series_description']
            series_types[desc] = series_types.get(desc, 0) + 1
    
    logger.info("\nSeries types:")
    for desc, count in sorted(series_types.items(), key=lambda x: -x[1]):
        logger.info(f"  {desc}: {count}")
    
    # Show directory structure
    logger.info("\n" + "="*80)
    logger.info("DIRECTORY STRUCTURE")
    logger.info("="*80)
    logger.info(f"{repo_dir}/")
    logger.info("└── data/")
    logger.info("    ├── study_metadata.json")
    logger.info("    └── dicoms/")
    
    # Show first 3 studies as examples
    sample_studies = sorted(list(studies_metadata.keys()))[:3]
    for study_id in sample_studies:
        logger.info(f"        ├── {study_id}/")
        study_data = studies_metadata[study_id]
        for idx, series in enumerate(study_data['series']):
            series_id = series['series_id']
            num_slices = series['num_slices']
            prefix = "└──" if idx == len(study_data['series']) - 1 else "├──"
            logger.info(f"        │   {prefix} {series_id}/")
            logger.info(f"        │       ├── 001.dcm")
            logger.info(f"        │       ├── 002.dcm")
            logger.info(f"        │       └── ... ({num_slices} files)")
    logger.info("        └── ...")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    logger.info("1. Copy entire github_upload/ directory to your lstv-annotation-tool repo")
    logger.info("2. Initialize Git LFS: git lfs install")
    logger.info("3. Add files: git add .")
    logger.info("4. Commit: git commit -m 'Add validation DICOM files'")
    logger.info("5. Push: git push origin main")
    logger.info("")
    logger.info(f"Output ready at: {output_base}")
    logger.info("="*80)

if __name__ == '__main__':
    main()
