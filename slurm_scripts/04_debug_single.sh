#!/bin/bash
#SBATCH -q gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --constraint=v100
#SBATCH --time=01:00:00
#SBATCH --job-name=lstv_debug
#SBATCH -o logs/debug_%j.out
#SBATCH -e logs/debug_%j.err

set -euo pipefail
set -x

# Get study ID from command line or use first available
STUDY_ID=${1:-}

echo "================================================================"
echo "LSTV Uncertainty Detection - DEBUG MODE (Single Study)"
echo "Study ID: ${STUDY_ID:-AUTO}"
echo "Job ID: $SLURM_JOB_ID"
echo "Start time: $(date)"
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
OUTPUT_DIR="${PROJECT_DIR}/data/output/debug"
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

echo "================================================================"
echo "Starting LSTV Uncertainty Inference - DEBUG MODE"
echo "================================================================"

# Build command
CMD="python /work/src/inference.py \
    --input_dir /data/input \
    --series_csv /data/raw/train_series_descriptions.csv \
    --output_dir /data/output \
    --checkpoint /app/models/point_net_checkpoint.pth \
    --mode debug"

if [[ -n "$STUDY_ID" ]]; then
    CMD="$CMD --debug_study_id $STUDY_ID"
fi

# Run inference
singularity exec --nv \
    --bind $PROJECT_DIR:/work \
    --bind $DATA_DIR:/data/input \
    --bind $OUTPUT_DIR:/data/output \
    --bind $MODELS_DIR:/app/models \
    --bind $(dirname $SERIES_CSV):/data/raw \
    --pwd /work \
    "$IMG_PATH" \
    $CMD

inference_exit=$?

if [ $inference_exit -ne 0 ]; then
    echo "ERROR: Inference failed"
    exit $inference_exit
fi

# Generate report with embedded images
echo ""
echo "================================================================"
echo "Generating HTML Report with Embedded Images..."
echo "================================================================"

singularity exec \
    --bind $PROJECT_DIR:/work \
    --bind $OUTPUT_DIR:/data/output \
    --bind $DATA_DIR:/data/input \
    --bind $(dirname $SERIES_CSV):/data/raw \
    --pwd /work \
    "$IMG_PATH" \
    python /work/src/generate_report.py \
        --csv /data/output/lstv_uncertainty_metrics.csv \
        --output /data/output/report.html \
        --data_dir /data/input \
        --series_csv /data/raw/train_series_descriptions.csv \
        --debug_dir /data/output/debug_visualizations

echo "================================================================"
echo "Complete!"
echo "End time: $(date)"
echo "================================================================"

echo ""
echo "RESULTS:"
echo "  CSV: ${OUTPUT_DIR}/lstv_uncertainty_metrics.csv"
echo "  Report: ${OUTPUT_DIR}/report.html"
echo "  Visualizations: ${OUTPUT_DIR}/debug_visualizations/"
echo ""
echo "View results:"
echo "  cat ${OUTPUT_DIR}/lstv_uncertainty_metrics.csv"
echo "  firefox ${OUTPUT_DIR}/report.html"
echo ""
echo "Report includes:"
echo "  - Debug matplotlib plots (from --debug_dir)"
echo "  - Embedded DICOM images (sagittal + axial)"
echo "  - Interactive Plotly visualizations"
echo "================================================================"
