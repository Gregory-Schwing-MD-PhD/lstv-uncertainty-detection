#!/bin/bash
#SBATCH -q primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --job-name=extract_validation_dicoms
#SBATCH -o logs/extract_dicoms_%j.out
#SBATCH -e logs/extract_dicoms_%j.err
#SBATCH --mail-user=go2432@wayne.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

# ==============================================================================
# 1. ENVIRONMENT SETUP (EXACT COPY FROM SCRIPT A)
# ==============================================================================
# EXACT SAME SINGULARITY SETUP AS 02_trial_inference.sh
export SINGULARITY_TMPDIR="/tmp/${USER}_job_${SLURM_JOB_ID}"
export XDG_RUNTIME_DIR="$SINGULARITY_TMPDIR/runtime"
export NXF_SINGULARITY_CACHEDIR="${HOME}/singularity_cache"

# EXACT SAME ENVIRONMENT
export CONDA_PREFIX="${HOME}/mambaforge/envs/nextflow"
export PATH="${CONDA_PREFIX}/bin:$PATH"
unset JAVA_HOME
unset LD_LIBRARY_PATH
unset PYTHONPATH
unset R_LIBS
unset R_LIBS_USER
unset R_LIBS_SITE

# Uses same container
CONTAINER="docker://go2432/lstv-uncertainty:latest"
IMG_PATH="${NXF_SINGULARITY_CACHEDIR}/lstv-uncertainty.sif"

# ==============================================================================
# 2. LOGIC & CHECKS (FROM SCRIPT B)
# ==============================================================================
echo "================================================================"
echo "Extract Validation DICOMs for GitHub Upload"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
echo "Container: $IMG_PATH"
echo "================================================================"

# Define Project Directory
PROJECT_DIR="/wsu/home/go/go24/go2432/lstv-uncertainty-detection"
cd "$PROJECT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Checking required files..."
if [[ ! -f "models/valid_id.npy" ]]; then
    echo "ERROR: models/valid_id.npy not found"
    exit 1
fi

if [[ ! -f "data/raw/train_series_descriptions.csv" ]]; then
    echo "ERROR: data/raw/train_series_descriptions.csv not found"
    exit 1
fi

if [[ ! -d "data/raw/train_images" ]]; then
    echo "ERROR: data/raw/train_images directory not found"
    exit 1
fi

echo "✓ All required files found"

# ==============================================================================
# 3. EXECUTION
# ==============================================================================
echo "================================================================"
echo "Running extraction script in Singularity..."
echo "This will copy ~10-15GB of DICOM files"
echo "Estimated time: 30-60 minutes"
echo "================================================================"

# Ensure tmp dir exists
mkdir -p "$SINGULARITY_TMPDIR"

# Run singularity using Script A's environment variables
# We bind the current directory ($PROJECT_DIR) to /work so the script finds files locally
singularity exec \
    --bind "${PROJECT_DIR}:/work" \
    --bind "${PROJECT_DIR}/data/raw:/data/raw" \
    --bind "${PROJECT_DIR}/models:/app/models" \
    --pwd /work \
    "$IMG_PATH" \
    python extract_validation_dicoms.py

exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo "ERROR: Extraction failed with exit code $exit_code"
    exit $exit_code
fi

# ==============================================================================
# 4. SUMMARY (FROM SCRIPT B)
# ==============================================================================
echo "================================================================"
echo "Extraction complete!"
echo "End time: $(date)"
echo "================================================================"

OUTPUT_DIR="${PROJECT_DIR}/github_upload"
if [[ -d "$OUTPUT_DIR" ]]; then
    echo ""
    echo "Output directory size:"
    du -sh "$OUTPUT_DIR"
    echo ""
    echo "Number of DICOM files:"
    find "$OUTPUT_DIR" -name "*.dcm" | wc -l
    echo ""
    echo "Output location: $OUTPUT_DIR"
fi

echo ""
echo "================================================================"
echo "NEXT STEPS:"
echo "================================================================"
echo "1. Navigate to extraction output:"
echo "   cd ${OUTPUT_DIR}"
echo ""
echo "2. Review the extracted files:"
echo "   ls -lh data/"
echo "   cat data/study_metadata.json | head -20"
echo ""
echo "3. Copy to your lstv-annotation-tool repo directory"
echo "================================================================"
