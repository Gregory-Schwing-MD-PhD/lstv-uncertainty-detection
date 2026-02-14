#!/bin/bash
#SBATCH -q primary
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=48:00:00
#SBATCH --job-name=lstv_master
#SBATCH -o logs/master_%j.out
#SBATCH -e logs/master_%j.err
#SBATCH --mail-user=go2432@wayne.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail

echo "================================================================"
echo "LSTV Uncertainty Detection - MASTER PIPELINE"
echo "Assumes RSNA data already downloaded"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
echo "================================================================"

PROJECT_DIR="$(pwd)"
SLURM_DIR="${PROJECT_DIR}/slurm_scripts"
DATA_DIR="${PROJECT_DIR}/data/raw"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to submit job and wait for completion
submit_and_wait() {
    local script=$1
    local name=$2
    
    echo ""
    echo "================================================================"
    echo "STEP: $name"
    echo "================================================================"
    
    job_id=$(sbatch --parsable "$script")
    echo "Submitted job: $job_id"
    
    # Wait for job to complete
    while squeue -j $job_id 2>/dev/null | grep -q $job_id; do
        sleep 30
    done
    
    # Check if job succeeded
    if sacct -j $job_id --format=State | grep -q "COMPLETED"; then
        echo -e "${GREEN}✓ $name completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        echo "Check logs in logs/ directory"
        return 1
    fi
}

# Verify data exists
echo ""
echo "================================================================"
echo "Verifying RSNA data..."
echo "================================================================"

if [ ! -d "${DATA_DIR}/train_images" ]; then
    echo -e "${RED}ERROR: RSNA data not found at ${DATA_DIR}/train_images${NC}"
    echo ""
    echo "Please download data first:"
    echo "  sbatch slurm_scripts/01_download_data.sh"
    echo ""
    echo "Or manually download and extract:"
    echo "  kaggle competitions download -c rsna-2024-lumbar-spine-degenerative-classification"
    echo "  unzip -d ${DATA_DIR}/"
    exit 1
fi

if [ ! -f "${DATA_DIR}/train_series_descriptions.csv" ]; then
    echo -e "${RED}ERROR: Series CSV not found at ${DATA_DIR}/train_series_descriptions.csv${NC}"
    echo ""
    echo "Expected structure:"
    echo "  data/raw/"
    echo "  ├── train_images/"
    echo "  └── train_series_descriptions.csv"
    exit 1
fi

# Count studies
NUM_STUDIES=$(find "${DATA_DIR}/train_images" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo -e "${GREEN}✓ Data found${NC}"
echo "  Location: ${DATA_DIR}/train_images"
echo "  Studies: ${NUM_STUDIES}"
echo ""

# Check for model checkpoint
CHECKPOINT="${PROJECT_DIR}/models/point_net_checkpoint.pth"
if [ ! -f "$CHECKPOINT" ]; then
    echo -e "${YELLOW}⚠ Model checkpoint not found${NC}"
    echo "  Location checked: ${CHECKPOINT}"
    echo "  Downloading automatically..."
    
    if submit_and_wait "${SLURM_DIR}/01b_download_model.sh" "Model Checkpoint Download"; then
        echo -e "${GREEN}✓ Model downloaded${NC}"
    else
        echo -e "${YELLOW}WARNING: Model download failed - will run in MOCK mode${NC}"
    fi
else
    echo -e "${GREEN}✓ Model checkpoint found${NC}"
    echo "  Location: ${CHECKPOINT}"
    echo ""
fi

# Step 1: Trial inference
if submit_and_wait "${SLURM_DIR}/02_trial_inference.sh" "Trial Inference (10 studies)"; then
    echo "Trial inference completed"
    echo "  Report: ${PROJECT_DIR}/data/output/trial/report.html"
else
    echo -e "${YELLOW}WARNING: Trial inference failed${NC}"
    echo "Continuing to production anyway..."
fi

# Step 2: Production inference
if submit_and_wait "${SLURM_DIR}/03_prod_inference.sh" "Production Inference (all studies)"; then
    echo "Production inference completed"
    echo "  Report: ${PROJECT_DIR}/data/output/production/report.html"
else
    echo -e "${RED}ERROR: Production inference failed${NC}"
    exit 1
fi

echo ""
echo "================================================================"
echo -e "${GREEN}✓ MASTER PIPELINE COMPLETE!${NC}"
echo "End time: $(date)"
echo "================================================================"
echo ""
echo "RESULTS LOCATIONS:"
echo "  Trial Report:      ${PROJECT_DIR}/data/output/trial/report.html"
echo "  Production Report: ${PROJECT_DIR}/data/output/production/report.html"
echo "  Trial CSV:         ${PROJECT_DIR}/data/output/trial/lstv_uncertainty_metrics.csv"
echo "  Production CSV:    ${PROJECT_DIR}/data/output/production/lstv_uncertainty_metrics.csv"
echo ""
echo "To view production report:"
echo "  firefox ${PROJECT_DIR}/data/output/production/report.html"
echo ""
echo "Next steps:"
echo "  1. Review top LSTV candidates in report"
echo "  2. Compare trial vs production metrics"
echo "  3. Debug specific studies: sbatch slurm_scripts/04_debug_single.sh <study_id>"
echo ""
echo "================================================================"
