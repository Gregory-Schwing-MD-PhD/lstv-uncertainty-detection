# LSTV Detection via Epistemic Uncertainty

**Novel zero-shot detection using uncertainty from Ian Pan's RSNA 2024 2nd Place Spine Localizer**

Wayne State University School of Medicine | Tech Fair 2026

## 📄 Abstract

**Zero-Shot Detection of Lumbosacral Transitional Vertebrae Using Epistemic Uncertainty from a Pretrained Spine Localizer**

*Gregory John Schwing*
*Department of Neurological Surgery, Wayne State University School of Medicine, Detroit, MI, 48201, United States*

**INTRODUCTION.** Lumbosacral transitional vertebrae (LSTV) are congenital spinal anomalies occurring in 15-30% of the population, characterized by sacralization of L5 or lumbarization of S1. Misidentification leads to wrong-level surgery, failed back surgery syndrome, and medicolegal consequences. Traditional detection requires expert radiologist review or supervised learning models trained on labeled LSTV datasets. Recent work by Kwak et al. (2025) demonstrated automated LSTV detection on plain radiographs using supervised ResNet-50, achieving 85.1% sensitivity and 61.9% specificity. However, this approach requires extensive LSTV-labeled training data. We hypothesized that a deep learning spine localizer trained exclusively on normal anatomy would exhibit high epistemic uncertainty when encountering LSTV, enabling zero-shot detection without LSTV-specific training data. The purpose of this study was to develop and validate an automated LSTV screening system using uncertainty quantification from a pretrained vertebral level localization model.

**METHODS.** We repurposed a heatmap regression network (UNet architecture) from the RSNA 2024 Lumbar Spine Degenerative Classification 2nd place solution, originally trained on 1,975 normal MRI studies for L1-S1 localization. The model outputs probability heatmaps for each vertebral level. We calculated Shannon entropy H = -Σp(x)log(p(x)) and peak confidence from L4-L5 and L5-S1 heatmaps as uncertainty metrics. SPINEPS vertebral centroids were used to anchor inference to anatomically verified disc locations rather than relying on the image center. Inference was performed on sagittal T2-weighted MRI studies from the RSNA validation set (held-out during original training) to prevent data leakage. Ground truth LSTV status will be established through expert radiologist review of a stratified audit queue of the 60 most ambiguous cases. Detection thresholds will be optimized using receiver operating characteristic analysis following audit completion.

**RESULTS.** Pending radiologist audit. Inference pipeline is complete and running on the validation cohort. Per-level entropy distributions and uncertainty-based labels are being generated. Final sensitivity, specificity, and AUROC will be reported following the clinical audit.

**CONCLUSIONS.** Pending audit completion. The centroid-guided uncertainty approach anchors model inference to anatomically verified vertebral locations, addressing the "blind counting" limitation of global heatmap analysis. If the entropy signal separates LSTV from normal anatomy as hypothesized, this will represent a true zero-shot detection method requiring no LSTV-labeled training data, with potential generalizability to other congenital spinal anomalies.

---

## 🎯 Overview

This project repurposes a spinal level localizer trained on normal anatomy to detect Lumbosacral Transitional Vertebrae (LSTV) by measuring epistemic uncertainty. When the model encounters LSTV (sacralized L5 or lumbarized S1), it exhibits high confusion/entropy because the anatomy doesn't match its learned patterns.

**Key Innovation:** Instead of training a new LSTV detector, we use uncertainty as a feature — a zero-shot detection approach. Rather than running inference globally on the image center, we use SPINEPS 3D vertebral centroids to guide the model to look *exactly where each bone is*, producing anatomically anchored uncertainty estimates per disc level.

**Baseline for comparison:** Kwak et al. (2025) achieved 85.1% sensitivity and 61.9% specificity using supervised ResNet-50 on plain radiographs, requiring 3,116 labeled training cases.

## 📊 Methodology

### Pipeline Overview

```
1. SPINEPS segmentation  (spineps-segmentation repo)
   └── *_seg-vert_msk.nii.gz  — instance mask per study
   └── *_ctd.json             — vertebral centroids (world coordinates, mm)

2. Centroid-guided uncertainty inference  (THIS REPO)
   For each disc level (L1/L2 through L5/S1):
     a. Load centroid world coordinates from SPINEPS ctd.json
     b. Convert world → voxel using NIfTI affine inverse
     c. Extract 160×160 sagittal patch centered on that vertebra
     d. Run Ian Pan UNet → local probability heatmap
     e. Measure Shannon entropy H at that specific bone location
     f. Re-label:
          H > 5.0          → LSTV_Verified
          H 4.0 – 5.0      → Ambiguous
          H < 4.0          → Normal_Confirmed
   └── lstv_uncertainty_metrics.csv
   └── relabeled_masks/  (*_relabeled.nii.gz + companion .json)
   └── audit_queue/high_priority_audit.json  (top-60 ambiguous cases)

3. Clinical audit  (lstv-annotation-tool repo)
   └── Radiologist reviews high_priority_audit.json
   └── audit_results.json  (ground truth labels)

4. Fusion + performance metrics  (lstv-fusion repo)
   └── sensitivity, specificity, AUROC
```

### Why Centroid-Guided Inference?

The naive approach runs the model on the middle slice of the whole volume. This has two failure modes: the middle slice may not contain L5/S1, and global entropy conflates uncertainty from multiple levels. Centroid-guided inference solves both: SPINEPS identifies where each vertebra physically is in 3D, and the model is run on a patch at exactly that location.

### Critical: Validation Set Only

**⚠️ To avoid data leakage, inference MUST only use validation set studies.**

The model was trained on studies from `train_id.npy`. We **ONLY** run inference on studies in `valid_id.npy` held out during training.

**Files Required:**
- `models/point_net_checkpoint.pth` — Trained model weights (130 MB)
- `models/valid_id.npy` — **Validation study IDs**

Both are automatically downloaded by `slurm_scripts/01b_download_model.sh`.

### Uncertainty Thresholds

| L5/S1 Entropy | Label | Interpretation |
|---------------|-------|----------------|
| > 5.0 | `LSTV_Verified` | Model highly confused — strong LSTV candidate |
| 4.0 – 5.0 | `Ambiguous` | Uncertain — enters audit queue |
| < 4.0 | `Normal_Confirmed` | Model confident — normal lumbosacral anatomy |

These thresholds are tunable and will be finalized by ROC analysis after the clinical audit.

## 🚀 Quick Start

### Prerequisites

SPINEPS segmentation output must exist before running centroid-guided inference:
```bash
# In spineps-segmentation repo:
sbatch slurm_scripts/02_spineps_segmentation.sh
# Produces: results/spineps_segmentation/segmentations/*_ctd.json
```

### On HPC Cluster

```bash
# 1. Clone repository
git clone <repo-url>
cd lstv-uncertainty-detection

# 2. Build Docker container (on local machine with Docker)
cd docker && ./build_and_push.sh && cd ..

# 3. Setup Kaggle credentials (only if downloading data)
mkdir -p ~/.kaggle
chmod 600 ~/.kaggle/kaggle.json

# 4. Download model checkpoint
sbatch slurm_scripts/01b_download_model.sh

# 5. Run centroid-guided inference (recommended)
sbatch slurm_scripts/04_centroid_inference.sh

# OR run global inference (legacy — no centroid anchoring)
sbatch slurm_scripts/03_prod_inference.sh
```

### Local Development

```bash
pip install -r requirements.txt

python src/inference_centroid.py \
    --input_dir data/raw/train_images \
    --series_csv data/raw/train_series_descriptions.csv \
    --centroid_dir /path/to/spineps_segmentation/segmentations \
    --seg_dir /path/to/spineps_segmentation/segmentations \
    --output_dir data/output/trial \
    --mode trial

python src/generate_report.py \
    --csv data/output/trial/lstv_uncertainty_metrics.csv \
    --output data/output/trial/report.html
```

## 📁 Project Structure

```
lstv-uncertainty-detection/
├── docker/
│   └── Dockerfile                       # pytorch/pytorch:2.3.1-cuda12.1 base
├── src/
│   ├── inference.py                     # Legacy: global middle-slice inference
│   ├── inference_centroid.py            # ★ Centroid-guided inference (recommended)
│   └── generate_report.py              # HTML report generator
├── slurm_scripts/
│   ├── 00_master_pipeline.sh            # Orchestrates full workflow
│   ├── 01_download_data.sh             # Download RSNA dataset
│   ├── 01b_download_model.sh           # Download model checkpoint
│   ├── 02_trial_inference.sh           # Trial run (10 studies)
│   ├── 03_prod_inference.sh            # Production — global inference (legacy)
│   ├── 04_centroid_inference.sh        # ★ Production — centroid-guided (recommended)
│   └── 05_debug_single.sh             # Debug single study
├── web/
│   ├── app.py                          # Flask demo application
│   └── templates/
│       └── demo.html                   # Interactive demo interface
├── data/
│   ├── raw/                            # RSNA dataset
│   └── output/                         # Results and reports
├── models/                             # Model checkpoints
├── logs/                               # SLURM logs
└── README.md
```

## 📊 Output Files

### From `inference_centroid.py`

```
data/output/centroid_inference/
├── lstv_uncertainty_metrics.csv        # Main results — one row per study
├── relabeled_masks/
│   ├── {study_id}_relabeled.nii.gz     # Instance mask (integer labels preserved)
│   └── {study_id}_relabeled.json       # Per-vertebra uncertainty + LSTV status
└── audit_queue/
    └── high_priority_audit.json        # Top-60 ambiguous cases for radiologist review
```

**CSV columns:**
- `study_id`, `series_id`
- `{level}_confidence`, `{level}_entropy`, `{level}_spatial_entropy` (l1_l2 through l5_s1)
- `centroid_guided` — whether SPINEPS centroids were available for this study
- `n_centroid_levels` — how many of 5 levels used centroid anchoring (0–5)
- `lstv_label` — `LSTV_Verified` | `Ambiguous` | `Normal_Confirmed`
- `lstv_confidence_pct` — 0–100% scaled confidence in the label

**Relabeled mask companion JSON:**
```json
{
  "study_id": "1020394063",
  "lstv_label": "LSTV_Verified",
  "lstv_confidence_pct": 78.5,
  "l5_s1_entropy": 6.14,
  "entropy_threshold_lstv": 5.0,
  "instance_labels": {
    "24": {"vertebra_name": "L5", "lstv_status": "LSTV_Verified", ...},
    "26": {"vertebra_name": "Sacrum", "lstv_status": "LSTV_Verified", ...}
  }
}
```

## 🔧 Configuration

### Model Checkpoint & Validation IDs

**Option 1: Automated Download (Recommended)**
```bash
sbatch slurm_scripts/01b_download_model.sh
```
Downloads `00002484.pth` and `valid_id.npy` from `hengck23/rsna2024-demo-workflow`.

**Option 2: Manual Download**
1. Go to: https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
2. Download `00002484.pth` → `models/point_net_checkpoint.pth`
3. Download `valid_id.npy` → `models/valid_id.npy`

### Entropy Thresholds

Defaults in `inference_centroid.py`:
```python
ENTROPY_LSTV      = 5.0   # above → LSTV_Verified
ENTROPY_AMBIGUOUS = 4.0   # between → Ambiguous; below → Normal_Confirmed
```

### Container

Built on `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime`. Pip-only (no Conda) for fast builds. DICOM decompression via `python-gdcm` + `pylibjpeg`.

```bash
cd docker && ./build_and_push.sh
singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest
```

## 🎓 Execution Modes

**Centroid-guided production (recommended):**
```bash
sbatch slurm_scripts/04_centroid_inference.sh
```

**Trial (10 studies, sanity check):**
```bash
MODE=trial sbatch slurm_scripts/04_centroid_inference.sh
```

**Debug single study:**
```bash
sbatch slurm_scripts/05_debug_single.sh <study_id>
```

**Legacy global inference (no SPINEPS required):**
```bash
sbatch slurm_scripts/03_prod_inference.sh
```

## 🔍 Interpreting Results

- **`LSTV_Verified`:** Model encountered anatomy at L5/S1 that didn't match its training distribution. Strong candidate for radiologist review.
- **`Ambiguous`:** Enters the audit queue. Model is uncertain but not strongly signaling LSTV.
- **`Normal_Confirmed`:** Model confident at that centroid location. Standard lumbosacral anatomy.

The `n_centroid_levels` column tells you how many of the 5 disc levels used centroid anchoring. Studies where SPINEPS failed or centroids were outside the image volume fall back to global middle-slice inference — check this column to identify any quality issues.

## 🐛 Troubleshooting

```bash
# Verify container
singularity exec lstv-uncertainty.sif python --version
singularity exec --nv lstv-uncertainty.sif nvidia-smi

# Check job logs
tail -f logs/centroid_<job_id>.out
tail -f logs/centroid_<job_id>.err

# Verify centroid files exist
ls results/spineps_segmentation/segmentations/*_ctd.json | wc -l

# Check for fallback cases (n_centroid_levels < 5)
awk -F',' 'NR>1 && $4<5 {print $1, $4}' data/output/centroid_inference/lstv_uncertainty_metrics.csv
```

## 📚 References

1. **Kwak et al. - Automated Detection of LSTV Using Deep Learning (2025)**
   - Journal of Clinical Medicine, 14(21), 7671
   - DOI: https://doi.org/10.3390/jcm14217671
   - Supervised baseline: 85.1% sensitivity, 61.9% specificity

2. **Ian Pan - RSNA 2024 Lumbar Spine Degenerative Classification (2nd Place)**
   - https://www.kaggle.com/code/yujiariyasu/rsna-lumbar-spine-2nd-place-solution

3. **Point Net Model Checkpoint**
   - https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
   - Original author: hengck23

4. **Gal & Ghahramani - Dropout as a Bayesian Approximation (2016)**

5. **Castellvi et al. - LSTV Classification (1984)**

## 👥 Team

**Wayne State University School of Medicine**
- Gregory John Schwing, Department of Neurological Surgery

## 📝 Citation

```bibtex
@software{lstv_uncertainty_2026,
  title={Zero-Shot LSTV Detection via Centroid-Guided Epistemic Uncertainty},
  author={Gregory John Schwing},
  year={2026},
  organization={Wayne State University School of Medicine},
  note={Pending clinical audit and validation}
}

@article{kwak2025automated,
  title={Automated Detection of Lumbosacral Transitional Vertebrae on Plain Lumbar Radiographs Using a Deep Learning Model},
  author={Kwak, Donghyuk and Ro, Du Hyun and Kang, Dong-Ho},
  journal={Journal of Clinical Medicine},
  volume={14},
  number={21},
  pages={7671},
  year={2025},
  publisher={MDPI}
}
```

## 🔗 Links

- **RSNA Competition**: https://www.kaggle.com/competitions/rsna-2024-lumbar-spine-degenerative-classification
- **Ian Pan's Solution**: https://www.kaggle.com/competitions/rsna-2024-lumbar-spine-degenerative-classification/writeups/ianpan-kevin-yuji-bartley-2nd-place-solution
- **Kwak et al. Paper**: https://doi.org/10.3390/jcm14217671

## 📄 License

MIT License — See LICENSE file for details

## 🎉 Acknowledgments

- Kwak et al. for establishing the supervised learning baseline
- Ian Pan and hengck23 for open-sourcing the RSNA solution and checkpoint
- RSNA for the lumbar spine dataset
- Wayne State University for computational resources
