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
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
echo "================================================================"

PROJECT_DIR="$(pwd)"
SLURM_DIR="${PROJECT_DIR}/slurm_scripts"

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
        echo "✓ $name completed successfully"
        return 0
    else
        echo "✗ $name FAILED"
        echo "Check logs in logs/ directory"
        return 1
    fi
}

# Step 1: Download data
if submit_and_wait "${SLURM_DIR}/01_download_data.sh" "Data Download"; then
    echo "Data download completed"
else
    echo "ERROR: Data download failed"
    exit 1
fi

# Step 1b: Download model checkpoint
if submit_and_wait "${SLURM_DIR}/01b_download_model.sh" "Model Checkpoint Download"; then
    echo "Model checkpoint download completed"
else
    echo "WARNING: Model download failed - will run in MOCK mode"
fi

# Step 2: Trial inference
if submit_and_wait "${SLURM_DIR}/02_trial_inference.sh" "Trial Inference"; then
    echo "Trial inference completed"
else
    echo "ERROR: Trial inference failed"
    echo "Continuing to production anyway..."
fi

# Step 3: Production inference
if submit_and_wait "${SLURM_DIR}/03_prod_inference.sh" "Production Inference"; then
    echo "Production inference completed"
else
    echo "ERROR: Production inference failed"
    exit 1
fi

echo ""
echo "================================================================"
echo "MASTER PIPELINE COMPLETE!"
echo "End time: $(date)"
echo "================================================================"
echo ""
echo "RESULTS LOCATIONS:"
echo "  Trial: ${PROJECT_DIR}/data/output/trial/report.html"
echo "  Production: ${PROJECT_DIR}/data/output/production/report.html"
echo ""
echo "To view results:"
echo "  firefox ${PROJECT_DIR}/data/output/production/report.html"
echo "================================================================"
