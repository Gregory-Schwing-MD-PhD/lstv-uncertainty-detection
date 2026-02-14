# ✅ LSTV Uncertainty Detection - Final Package Summary

## 🎁 What You're Getting

**Tarball:** `lstv-uncertainty-detection.tar.gz` (30 KB)

### ⭐ Latest Updates:

1. **✅ PyTorch 2.3.1 + CUDA 12.1**
   - Updated Dockerfile to use `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime`
   - Matches your existing Docker Hub image

2. **✅ Docker Build & Push Script**
   - New file: `docker/build_and_push.sh`
   - Automated build, test, and push to `go2432/lstv-uncertainty:latest`
   - Interactive prompts for safety

3. **✅ Master Pipeline (No Download)**
   - New file: `slurm_scripts/00_master_pipeline_no_download.sh`
   - Assumes RSNA data already downloaded
   - Optionally downloads model checkpoint
   - Saves ~24 hours!

4. **✅ Model Checkpoint Download Script** ⭐ NEW
   - New file: `slurm_scripts/01b_download_model.sh`
   - Downloads Point Net checkpoint from Kaggle
   - Source: `hengck23/rsna2024-demo-workflow`
   - File: `00002484.pth` → `models/point_net_checkpoint.pth`
   - Size: 130 MB, Time: ~5-10 minutes

5. **✅ Updated References** ⭐ NEW
   - Added Ian Pan's Kaggle notebook link
   - Added model checkpoint dataset link
   - Proper attribution to original authors

## 📦 Complete Contents (26 files)

### Documentation (5)
- README.md (with Kaggle links)
- USAGE.md (updated workflow)
- QUICKSTART.md
- MANIFEST.md
- LICENSE

### Python Code (3)
- src/inference.py (350 lines)
- src/generate_report.py (400 lines)
- web/app.py (200 lines)

### SLURM Scripts (8) ⭐
- 00_master_pipeline.sh (downloads data + model)
- **00_master_pipeline_no_download.sh** (data exists)
- 01_download_data.sh (RSNA dataset)
- **01b_download_model.sh** (Point Net checkpoint) ⭐ NEW
- 02_trial_inference.sh (10 studies)
- 03_prod_inference.sh (all studies)
- 04_debug_single.sh (single study debug)
- All executable and ready to run

### Docker (2)
- Dockerfile (PyTorch 2.3.1 CUDA 12.1)
- build_and_push.sh (automated build)

### Web Demo (1 HTML + 1 Python)
- web/templates/demo.html (400 lines)

### Config (4)
- config/config.json
- requirements.txt
- setup.sh
- .gitignore

## 🚀 Quick Start Guide

### Step 1: Build Docker (Local Machine)
```bash
tar -xzf lstv-uncertainty-detection.tar.gz
cd lstv-uncertainty-detection/docker
./build_and_push.sh
```

**What happens:**
- Builds using PyTorch 2.3.1 + CUDA 12.1
- Tests Python, PyTorch, pydicom imports
- Asks: "Push to Docker Hub? (y/n)"
- Pushes to `go2432/lstv-uncertainty:latest`

### Step 2: Deploy to Cluster
```bash
# Copy to cluster
scp -r lstv-uncertainty-detection/ user@cluster:~/

# SSH to cluster
ssh user@cluster
cd lstv-uncertainty-detection

# Run setup
./setup.sh
```

### Step 3: Download Model Checkpoint
```bash
# Automated download
sbatch slurm_scripts/01b_download_model.sh

# OR manual download
# 1. Go to: https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
# 2. Download: 00002484.pth
# 3. Place at: models/point_net_checkpoint.pth
```

### Step 4: Run Pipeline
```bash
# If RSNA data already downloaded (RECOMMENDED)
sbatch slurm_scripts/00_master_pipeline_no_download.sh

# OR download everything first
sbatch slurm_scripts/00_master_pipeline.sh

# OR step-by-step
sbatch slurm_scripts/01_download_data.sh      # Optional: RSNA data
sbatch slurm_scripts/01b_download_model.sh    # Optional: Model checkpoint
sbatch slurm_scripts/02_trial_inference.sh    # Trial run
sbatch slurm_scripts/03_prod_inference.sh     # Full dataset
```

### Step 5: View Results
```bash
# Check job
squeue -u $USER

# View logs
tail -f logs/master_*.out

# Open report when done
firefox data/output/production/report.html
```

## 📚 Model Checkpoint Details

### What is it?
The **Point Net** model from Ian Pan's RSNA 2024 2nd place solution. It performs heatmap regression to localize vertebral levels (L1-L5) on sagittal T2 MRI scans.

### Where to get it?
**Option 1: Automated (Recommended)**
```bash
sbatch slurm_scripts/01b_download_model.sh
```

**Option 2: Manual**
1. Dataset: https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
2. File: `00002484.pth` (130 MB)
3. Rename to: `point_net_checkpoint.pth`
4. Place in: `models/`

### Why do we need it?
This checkpoint is trained on normal spine anatomy. When it encounters LSTV, it shows high uncertainty (entropy), which we use for zero-shot LSTV detection!

### What if I don't have it?
The pipeline runs in **MOCK mode** with synthetic uncertainty values for testing. You can still validate the entire pipeline works, but results won't be real.

## 📊 Pipeline Options Explained

### Option 1: Full Pipeline with Downloads ⭐ EASIEST
```bash
sbatch slurm_scripts/00_master_pipeline.sh
```
**Downloads:**
- ✓ RSNA dataset (~150 GB, ~4-6 hours)
- ✓ Model checkpoint (130 MB, ~10 minutes)

**Runs:**
- ✓ Trial inference (10 studies)
- ✓ Production inference (all studies)

**Total Time:** ~30-36 hours

### Option 2: Pipeline (Data Already Downloaded) ⭐ FASTEST
```bash
sbatch slurm_scripts/00_master_pipeline_no_download.sh
```
**Requires:**
- ✓ RSNA data in `data/raw/train_images/`

**Optionally downloads:**
- ? Model checkpoint (asks interactively)

**Runs:**
- ✓ Trial inference (10 studies)
- ✓ Production inference (all studies)

**Total Time:** ~6-8 hours

### Option 3: Step-by-Step ⭐ MOST CONTROL
```bash
# Download data (optional)
sbatch slurm_scripts/01_download_data.sh

# Download model (optional)
sbatch slurm_scripts/01b_download_model.sh

# Run trial
sbatch slurm_scripts/02_trial_inference.sh

# Run production
sbatch slurm_scripts/03_prod_inference.sh
```

**Total Time:** Varies based on what you skip

### Option 4: Debug Mode
```bash
sbatch slurm_scripts/04_debug_single.sh <study_id>
```
**Best for:**
- Testing specific cases
- Debugging issues
- Creating visualizations

## 🔗 Important Links

### Ian Pan's Solution
- **Kaggle Notebook:** https://www.kaggle.com/code/yujiariyasu/rsna-lumbar-spine-2nd-place-solution
- **Author:** Yuji Ariyasu (yujiariyasu)
- **Ranking:** 2nd Place in RSNA 2024 Lumbar Spine Competition

### Model Checkpoint
- **Dataset:** https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
- **Author:** hengck23
- **File:** 00002484.pth (130 MB)
- **Purpose:** Vertebral level localization via heatmap regression

### RSNA Competition
- **Competition:** RSNA 2024 Lumbar Spine Degenerative Classification
- **Data:** ~500 studies with sagittal/axial T1/T2 MRI
- **Task:** Classify degenerative conditions at 5 vertebral levels

## 🎯 Expected Outputs

### After Trial Run (30 minutes)
- `data/output/trial/lstv_uncertainty_metrics.csv`
- `data/output/trial/report.html`
- Validates pipeline works on 10 studies

### After Production Run (4-6 hours)
- `data/output/production/lstv_uncertainty_metrics.csv`
- `data/output/production/report.html`
- Complete LSTV analysis on all studies

### CSV Columns
- `study_id`, `series_id`
- `l1_l2_confidence`, `l1_l2_entropy`, `l1_l2_spatial_entropy`
- `l2_l3_confidence`, `l2_l3_entropy`, `l2_l3_spatial_entropy`
- `l3_l4_confidence`, `l3_l4_entropy`, `l3_l4_spatial_entropy`
- `l4_l5_confidence`, `l4_l5_entropy`, `l4_l5_spatial_entropy`
- `l5_s1_confidence`, `l5_s1_entropy`, `l5_s1_spatial_entropy` ← **KEY METRICS**

### HTML Report Sections
1. **Statistics Dashboard**
   - Total studies analyzed
   - High/Medium/Low risk counts
   - LSTV detection rate

2. **Distribution Plots**
   - Entropy histograms per level
   - Confidence box plots
   - L5-S1 scatter plot

3. **Top LSTV Candidates**
   - Ranked by L5-S1 entropy
   - Top 20 studies for radiologist review

4. **Level Comparison**
   - Mean ± std entropy/confidence
   - Cross-level analysis

## 🔧 Technical Specifications

### Docker Container
- **Image:** `go2432/lstv-uncertainty:latest`
- **Base:** PyTorch 2.3.1, CUDA 12.1, cuDNN 8
- **Python:** 3.10
- **Size:** ~3-4 GB
- **Platform:** linux/amd64

### SLURM Resources
| Job | Time | Memory | CPUs | GPU |
|-----|------|--------|------|-----|
| Download Data | 24h | 16GB | 4 | None |
| Download Model | 1h | 8GB | 2 | None |
| Trial | 2h | 32GB | 4 | 1x V100 |
| Production | 24h | 64GB | 8 | 1x V100 |
| Debug | 1h | 32GB | 4 | 1x V100 |

### Dependencies
All in `requirements.txt`:
- torch >= 2.0.0
- pydicom 2.4.4
- nibabel 5.2.0
- timm 0.9.10
- albumentations 1.3.1
- opencv-python, matplotlib, plotly
- Flask (web demo)
- And more...

## 🆘 Common Issues

### Issue: "Model checkpoint not found"
**Solution:**
```bash
sbatch slurm_scripts/01b_download_model.sh
```
OR download manually and place at `models/point_net_checkpoint.pth`

### Issue: "Kaggle credentials not found"
**Solution:**
```bash
mkdir -p ~/.kaggle
# Download kaggle.json from https://www.kaggle.com/settings
cp ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

### Issue: "RSNA data not found"
**Solution:**
```bash
sbatch slurm_scripts/01_download_data.sh
```
OR download manually and extract to `data/raw/`

### Issue: "Docker push failed"
**Solution:**
```bash
docker login
# Enter: go2432
# Password: [your Docker Hub token]
cd docker
./build_and_push.sh
```

### Issue: "Container pull fails on cluster"
**Solution:**
```bash
# Check cache directory
ls $HOME/singularity_cache/

# Manual pull
singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest

# Verify
singularity exec lstv-uncertainty.sif python --version
```

## 📋 Pre-Flight Checklist

Before running full pipeline:
- [ ] Docker Hub repo created: `go2432/lstv-uncertainty`
- [ ] Container built and pushed locally
- [ ] Tarball extracted on cluster
- [ ] Setup script run: `./setup.sh`
- [ ] Kaggle credentials configured (if downloading)
- [ ] RSNA data downloaded (or will be downloaded)
- [ ] Model checkpoint downloaded (or will run in MOCK mode)
- [ ] SLURM scripts are executable (`chmod +x slurm_scripts/*.sh`)

## 🎉 You're Ready!

Everything you need is in:
**`lstv-uncertainty-detection.tar.gz`**

### Quick Commands Recap:
```bash
# Build Docker locally
cd docker && ./build_and_push.sh

# Run on cluster (data exists)
sbatch slurm_scripts/00_master_pipeline_no_download.sh

# Download model only
sbatch slurm_scripts/01b_download_model.sh

# View results
firefox data/output/production/report.html
```

---

**Questions?** All documented in:
- README.md (overview + links)
- USAGE.md (detailed guide)
- QUICKSTART.md (fast reference)
- MANIFEST.md (file listing)
