#!/bin/bash
#SBATCH -q gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --constraint=v100
#SBATCH --time=24:00:00
#SBATCH --job-name=lstv_prod
#SBATCH -o logs/prod_%j.out
#SBATCH -e logs/prod_%j.err
#SBATCH --mail-user=go2432@wayne.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail
set -x

echo "================================================================"
echo "LSTV Uncertainty Detection - PRODUCTION MODE (Full Dataset)"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
echo "Assigned GPUs: $CUDA_VISIBLE_DEVICES"
echo "================================================================"

nvidia-smi

# Singularity temp setup
export SINGULARITY_TMPDIR="/tmp/${USER}_job_${SLURM_JOB_ID}"
export XDG_RUNTIME_DIR="$SINGULARITY_TMPDIR/runtime"
export NXF_SINGULARITY_CACHEDIR="${HOME}/singularity_cache"
mkdir -p "$SINGULARITY_TMPDIR" "$XDG_RUNTIME_DIR" "$NXF_SINGULARITY_CACHEDIR"

trap 'rm -rf "$SINGULARITY_TMPDIR"' EXIT

# Environment
export CONDA_PREFIX="${HOME}/mambaforge/envs/nextflow"
export PATH="${CONDA_PREFIX}/bin:$PATH"
unset JAVA_HOME

which singularity

export NXF_SINGULARITY_HOME_MOUNT=true

unset LD_LIBRARY_PATH
unset PYTHONPATH
unset R_LIBS
unset R_LIBS_USER
unset R_LIBS_SITE

# Project paths
PROJECT_DIR="$(pwd)"
DATA_DIR="${PROJECT_DIR}/data/raw/train_images"
SERIES_CSV="${PROJECT_DIR}/data/raw/train_series_descriptions.csv"
OUTPUT_DIR="${PROJECT_DIR}/data/output/production"
MODELS_DIR="${PROJECT_DIR}/models"

mkdir -p $OUTPUT_DIR/logs
mkdir -p $MODELS_DIR

# Container
DOCKER_USERNAME="go2432"
CONTAINER="docker://${DOCKER_USERNAME}/lstv-uncertainty:latest"
IMG_PATH="${NXF_SINGULARITY_CACHEDIR}/lstv-uncertainty.sif"

if [[ ! -f "$IMG_PATH" ]]; then
    echo "Pulling container..."
    singularity pull "$IMG_PATH" "$CONTAINER"
fi

echo "Container ready: $IMG_PATH"

# Check for model checkpoint
CHECKPOINT="${MODELS_DIR}/point_net_checkpoint.pth"
if [[ ! -f "$CHECKPOINT" ]]; then
    echo "================================================================"
    echo "WARNING: Model checkpoint not found at $CHECKPOINT"
    echo "Running in MOCK mode with synthetic uncertainty data"
    echo "To use real model, place checkpoint at: $CHECKPOINT"
    echo "================================================================"
fi

echo "================================================================"
echo "Starting LSTV Uncertainty Inference - PRODUCTION MODE"
echo "Data: $DATA_DIR"
echo "Series CSV: $SERIES_CSV"
echo "Output: $OUTPUT_DIR"
echo "Models: $MODELS_DIR"
echo "================================================================"

# Run inference
singularity exec --nv \
    --bind $PROJECT_DIR:/work \
    --bind $DATA_DIR:/data/input \
    --bind $OUTPUT_DIR:/data/output \
    --bind $MODELS_DIR:/app/models \
    --bind $(dirname $SERIES_CSV):/data/raw \
    --pwd /work \
    "$IMG_PATH" \
    python /work/src/inference.py \
        --input_dir /data/input \
        --series_csv /data/raw/train_series_descriptions.csv \
        --output_dir /data/output \
        --checkpoint /app/models/point_net_checkpoint.pth \
        --valid_ids /app/models/valid_id.npy \
        --mode prod

inference_exit=$?

if [ $inference_exit -ne 0 ]; then
    echo "ERROR: Inference failed"
    exit $inference_exit
fi

# Generate report
echo ""
echo "================================================================"
echo "Generating HTML Report..."
echo "================================================================"

singularity exec \
    --bind $PROJECT_DIR:/work \
    --bind $OUTPUT_DIR:/data/output \
    --pwd /work \
    "$IMG_PATH" \
    python /work/src/generate_report.py \
        --csv /data/output/lstv_uncertainty_metrics.csv \
        --output /data/output/report.html

echo "================================================================"
echo "Complete!"
echo "End time: $(date)"
echo "================================================================"

echo ""
echo "RESULTS:"
echo "  CSV: ${OUTPUT_DIR}/lstv_uncertainty_metrics.csv"
echo "  Report: ${OUTPUT_DIR}/report.html"
echo "  Total Studies Processed: $(wc -l < ${OUTPUT_DIR}/lstv_uncertainty_metrics.csv)"
echo ""
echo "To view report:"
echo "  firefox ${OUTPUT_DIR}/report.html"
echo "================================================================"
