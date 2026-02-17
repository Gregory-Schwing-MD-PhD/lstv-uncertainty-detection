#!/bin/bash
#SBATCH -q gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --constraint=v100
#SBATCH --time=36:00:00
#SBATCH --job-name=lstv_centroid
#SBATCH -o logs/centroid_%j.out
#SBATCH -e logs/centroid_%j.err
#SBATCH --mail-user=go2432@wayne.edu
#SBATCH --mail-type=BEGIN,END,FAIL

set -euo pipefail
set -x

echo "================================================================"
echo "LSTV Centroid-Guided Uncertainty Inference"
echo "Job ID: $SLURM_JOB_ID"
echo "Start: $(date)"
echo "Assigned GPUs: $CUDA_VISIBLE_DEVICES"
echo "================================================================"

nvidia-smi

# --- Singularity temp setup (identical to 03_prod_inference.sh) ---
export SINGULARITY_TMPDIR="/tmp/${USER}_job_${SLURM_JOB_ID}"
export XDG_RUNTIME_DIR="$SINGULARITY_TMPDIR/runtime"
export NXF_SINGULARITY_CACHEDIR="${HOME}/singularity_cache"
mkdir -p "$SINGULARITY_TMPDIR" "$XDG_RUNTIME_DIR" "$NXF_SINGULARITY_CACHEDIR"
trap 'rm -rf "$SINGULARITY_TMPDIR"' EXIT

# --- Environment (identical to 03_prod_inference.sh) ---
export CONDA_PREFIX="${HOME}/mambaforge/envs/nextflow"
export PATH="${CONDA_PREFIX}/bin:$PATH"
unset JAVA_HOME
which singularity
export NXF_SINGULARITY_HOME_MOUNT=true
unset LD_LIBRARY_PATH PYTHONPATH R_LIBS R_LIBS_USER R_LIBS_SITE

# --- Paths ---
PROJECT_DIR="$(pwd)"
DATA_DIR="${PROJECT_DIR}/data/raw/train_images"
SERIES_CSV="${PROJECT_DIR}/data/raw/train_series_descriptions.csv"
MODELS_DIR="${PROJECT_DIR}/models"

# SPINEPS lives in a DIFFERENT repo directory.
# Defaults to ~/spineps-segmentation but can be overridden:
#   SPINEPS_REPO=/path/to/spineps-segmentation sbatch slurm_scripts/04_centroid_inference.sh
SPINEPS_REPO="${SPINEPS_REPO:-${HOME}/spineps-segmentation}"
SPINEPS_SEG_DIR="${SPINEPS_REPO}/results/spineps_segmentation/segmentations"

OUTPUT_DIR="${PROJECT_DIR}/data/output/centroid_inference"
mkdir -p "$OUTPUT_DIR/logs" "$OUTPUT_DIR/relabeled_masks" "$OUTPUT_DIR/audit_queue"

# --- Container (same as 03_prod_inference.sh) ---
CONTAINER="docker://go2432/lstv-uncertainty:latest"
IMG_PATH="${NXF_SINGULARITY_CACHEDIR}/lstv-uncertainty.sif"
if [[ ! -f "$IMG_PATH" ]]; then
    echo "Pulling container..."
    singularity pull "$IMG_PATH" "$CONTAINER"
fi

# --- Prerequisites check ---
echo "Looking for SPINEPS segmentations at: $SPINEPS_SEG_DIR"
if [[ ! -d "$SPINEPS_SEG_DIR" ]]; then
    echo "ERROR: SPINEPS segmentations not found: $SPINEPS_SEG_DIR"
    echo ""
    echo "Fix options:"
    echo "  1. Run spineps first:  cd ~/spineps-segmentation && sbatch slurm_scripts/02_spineps_segmentation.sh"
    echo "  2. Set the path:       SPINEPS_REPO=/wsu/home/go/go24/go2432/spineps-segmentation sbatch slurm_scripts/04_centroid_inference.sh"
    exit 1
fi

N_CTD=$(ls "$SPINEPS_SEG_DIR"/*_ctd.json 2>/dev/null | wc -l)
N_MASKS=$(ls "$SPINEPS_SEG_DIR"/*_seg-vert_msk.nii.gz 2>/dev/null | wc -l)
echo "Found $N_CTD centroid files, $N_MASKS instance masks"

CHECKPOINT="${MODELS_DIR}/point_net_checkpoint.pth"
[[ ! -f "$CHECKPOINT" ]] && echo "WARNING: Checkpoint not found — MOCK mode"

echo "================================================================"
echo "SPINEPS repo:  $SPINEPS_REPO"
echo "Segmentations: $SPINEPS_SEG_DIR"
echo "Output:        $OUTPUT_DIR"
echo "================================================================"

# --- Run inference ---
singularity exec --nv \
    --bind "$PROJECT_DIR":/work \
    --bind "$DATA_DIR":/data/input \
    --bind "$OUTPUT_DIR":/data/output \
    --bind "$MODELS_DIR":/app/models \
    --bind "$(dirname $SERIES_CSV)":/data/raw \
    --bind "$SPINEPS_SEG_DIR":/data/spineps \
    --pwd /work \
    "$IMG_PATH" \
    python /work/src/inference_centroid.py \
        --input_dir    /data/input \
        --series_csv   /data/raw/train_series_descriptions.csv \
        --centroid_dir /data/spineps \
        --seg_dir      /data/spineps \
        --output_dir   /data/output \
        --checkpoint   /app/models/point_net_checkpoint.pth \
        --valid_ids    /app/models/valid_id.npy \
        --mode prod

echo "================================================================"
echo "Complete! End: $(date)"
echo ""
echo "Outputs:"
echo "  CSV:         $OUTPUT_DIR/lstv_uncertainty_metrics.csv"
echo "  Re-labeled:  $OUTPUT_DIR/relabeled_masks/"
echo "  Audit queue: $OUTPUT_DIR/audit_queue/high_priority_audit.json"
echo ""
echo "Next step — run fusion:"
echo "  sbatch slurm_scripts/05_fusion.sh"
echo "================================================================"
