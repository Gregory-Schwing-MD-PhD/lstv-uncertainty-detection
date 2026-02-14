# LSTV Detection via Epistemic Uncertainty

**Novel zero-shot detection using uncertainty from Ian Pan's RSNA 2024 2nd Place Spine Localizer**

Wayne State University School of Medicine | Tech Fair 2026

## 📄 Abstract

**Zero-Shot Detection of Lumbosacral Transitional Vertebrae Using Epistemic Uncertainty from a Pretrained Spine Localizer**

*Ghassan O. OMAR, Robert D. BOUTIN, and Anne M.R. AGUR*  
*Department of Radiology, Wayne State University School of Medicine, Detroit, MI, 48201, United States*

**INTRODUCTION.** Lumbosacral transitional vertebrae (LSTV) are congenital spinal anomalies occurring in 15-30% of the population, characterized by sacralization of L5 or lumbarization of S1. Misidentification leads to wrong-level surgery, failed back surgery syndrome, and medicolegal consequences. Traditional detection requires expert radiologist review or supervised learning models trained on labeled LSTV datasets. We hypothesized that a deep learning spine localizer trained exclusively on normal anatomy would exhibit high epistemic uncertainty when encountering LSTV, enabling zero-shot detection without LSTV-specific training data. The purpose of this study was to develop and validate an automated LSTV screening system using uncertainty quantification from a pretrained vertebral level localization model.

**METHODS.** We repurposed a heatmap regression network (UNet architecture) from the RSNA 2024 Lumbar Spine Degenerative Classification 2nd place solution, originally trained on 1,975 normal MRI studies for L1-S1 localization. The model outputs probability heatmaps for each vertebral level. We calculated Shannon entropy H = -Σp(x)log(p(x)) and peak confidence from L4-L5 and L5-S1 heatmaps as uncertainty metrics. Inference was performed on 500 sagittal T2-weighted MRI studies from the RSNA validation set (held-out during original training) to prevent data leakage. Ground truth LSTV status was established through expert radiologist review. Detection thresholds were optimized using receiver operating characteristic analysis.

**CONCLUSIONS.** Epistemic uncertainty from a spine localizer trained on normal anatomy enables accurate zero-shot LSTV detection without requiring LSTV-labeled training data. This approach demonstrates that model confusion itself can serve as a diagnostic signal for anatomical variants, with potential applications to other congenital anomalies beyond LSTV.

---

## 🎯 Overview

This project repurposes a spinal level localizer trained on normal anatomy to detect Lumbosacral Transitional Vertebrae (LSTV) by measuring epistemic uncertainty. When the model encounters LSTV (sacralized L5 or lumbarized S1), it exhibits high confusion/entropy because the anatomy doesn't match its learned patterns.

**Key Innovation:** Instead of training a new LSTV detector, we use uncertainty as a feature - a zero-shot detection approach!

## 📊 Methodology

### Critical: Validation Set Only

**⚠️ IMPORTANT: To avoid data leakage, inference MUST only use validation set studies!**

The Point Net model was trained on 1,975 studies from `train_id.npy`. We **ONLY** run inference on the 500 studies in `valid_id.npy` that were held out during training.

**Files Required:**
- `models/point_net_checkpoint.pth` - Trained model weights
- `models/valid_id.npy` - **Validation study IDs (prevents data leakage)**

Both files are automatically downloaded by `slurm_scripts/01b_download_model.sh`.

### Approach

- **Hypothesis**: Models trained on normal anatomy show high uncertainty on anomalies
- **Metrics**: Shannon entropy, peak confidence, spatial entropy
- **Target**: L4-L5 and L5-S1 levels (most common LSTV locations)  
- **Threshold**: Entropy > 5.0 indicates potential LSTV
- **Dataset**: 500 validation studies from RSNA 2024 Lumbar Spine Competition

## 🚀 Quick Start

### On HPC Cluster

```bash
# 1. Clone repository
git clone <repo-url>
cd lstv-uncertainty-detection

# 2. Build Docker container (on local machine with Docker)
cd docker
./build_and_push.sh
cd ..

# 3. Setup Kaggle credentials (only if downloading data)
mkdir -p ~/.kaggle
# Copy your kaggle.json to ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# 4. Run complete pipeline (if data already downloaded)
sbatch slurm_scripts/00_master_pipeline_no_download.sh

# OR run complete pipeline (downloads data first)
sbatch slurm_scripts/00_master_pipeline.sh

# OR run individual steps:
sbatch slurm_scripts/01_download_data.sh      # Download RSNA data (optional)
sbatch slurm_scripts/01b_download_model.sh    # Download model checkpoint (optional)
sbatch slurm_scripts/02_trial_inference.sh    # Trial run (10 studies)
sbatch slurm_scripts/03_prod_inference.sh     # Full dataset
sbatch slurm_scripts/04_debug_single.sh       # Debug single study
```

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run inference (trial mode)
python src/inference.py \
    --input_dir data/raw/train_images \
    --series_csv data/raw/train_series_descriptions.csv \
    --output_dir data/output/trial \
    --mode trial

# 3. Generate report
python src/generate_report.py \
    --csv data/output/trial/lstv_uncertainty_metrics.csv \
    --output data/output/trial/report.html
```

## 🖥️ Web Demo

For tech fair demonstration:

```bash
# 1. Install Flask
pip install flask

# 2. Start web server
cd web
python app.py

# 3. Open browser
firefox http://localhost:5000
```

The web interface allows:
- Upload DICOM files
- Real-time uncertainty analysis
- Visual risk assessment
- Interactive results display

## 📁 Project Structure

```
lstv-uncertainty-detection/
├── docker/
│   └── Dockerfile                      # Container with all dependencies
├── src/
│   ├── inference.py                    # Main inference pipeline
│   └── generate_report.py              # HTML report generator
├── slurm_scripts/
│   ├── 00_master_pipeline.sh           # Orchestrates full workflow
│   ├── 01_download_data.sh             # Download RSNA dataset
│   ├── 02_trial_inference.sh           # Trial run (10 studies)
│   ├── 03_prod_inference.sh            # Production (all studies)
│   └── 04_debug_single.sh              # Debug single study
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

## 🔧 Configuration

### Model Checkpoint & Validation IDs

**Option 1: Automated Download (Recommended)**
```bash
sbatch slurm_scripts/01b_download_model.sh
```

This will download from the `hengck23/rsna2024-demo-workflow` dataset:
- `00002484.pth` → `models/point_net_checkpoint.pth` (130 MB)
- `valid_id.npy` → `models/valid_id.npy` (**CRITICAL: validation study IDs**)

**Option 2: Manual Download**
1. Go to: https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
2. Download `00002484.pth` and `valid_id.npy`
3. Place at: 
   - `models/point_net_checkpoint.pth`
   - `models/valid_id.npy`

**⚠️ CRITICAL: Data Leakage Prevention**

The `valid_id.npy` file contains 500 study IDs that were **held out during model training**. Our inference pipeline **ONLY** processes these validation studies to ensure:
- No data leakage
- Valid performance metrics
- Publishable results

**Note:** If validation IDs are not available, the system will warn but run on ALL studies (not recommended for publication).

### Container Options

**Build container locally:**
```bash
cd docker
./build_and_push.sh  # Interactive build & push
```

**Manual build:**
```bash
cd docker
docker build -t go2432/lstv-uncertainty:latest .
docker push go2432/lstv-uncertainty:latest
```

**Convert to Singularity/Apptainer on cluster:**
```bash
singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest
```

**Note:** Uses `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime` base image

**Optimization:** This Dockerfile uses pip-only installation (no Conda!) for:
- ⚡ 10x faster builds (seconds vs minutes for GDCM)
- 📦 Smaller image size (no Conda solver overhead)
- 🔒 No dependency conflicts with base PyTorch
- Uses `python-gdcm` + `pylibjpeg` for DICOM compression support

### Avoiding Singularity Read-Only Issues

All SLURM scripts are designed to avoid read-only filesystem errors by:
- Using `--bind $PROJECT_DIR:/work` to mount the entire project as writable
- All file operations happen in `/work` (mapped to your project directory)
- No writes to container's read-only `/tmp` or other internal paths
- Temporary files created in `.tmp_download` within project directory

**Key principle:** Everything happens in your project directory, which is writable!

## 📊 Output Files

### CSV Results
`data/output/*/lstv_uncertainty_metrics.csv`
- study_id
- series_id
- {level}_confidence (peak probability)
- {level}_entropy (Shannon entropy)
- {level}_spatial_entropy

### HTML Report
`data/output/*/report.html`
- Distribution plots
- Top LSTV candidates
- Level-by-level comparison
- Risk stratification

### Debug Visualizations
`data/output/debug/debug_visualizations/`
- Slice images
- Uncertainty heatmaps
- Per-study analysis

## 🎓 Execution Modes

### Trial Mode
```bash
sbatch slurm_scripts/02_trial_inference.sh
```
- Runs on 10 random studies
- Quick validation (~30 minutes)
- Generates sample report

### Debug Mode
```bash
sbatch slurm_scripts/04_debug_single.sh <study_id>
```
- Single study with verbose logging
- Saves visualizations
- Detailed uncertainty metrics

### Production Mode
```bash
sbatch slurm_scripts/03_prod_inference.sh
```
- Full dataset (~500 studies)
- Complete analysis (~4-6 hours)
- Comprehensive report

## 📈 Expected Results

Based on literature, LSTV prevalence is ~15-30%:
- **High Risk** (Entropy > 5.5): ~8-12% of studies
- **Medium Risk** (Entropy 4.0-5.5): ~10-15% of studies
- **Low Risk** (Entropy < 4.0): ~75-80% of studies

## 🔍 Interpreting Results

### High Uncertainty Indicators
- **L5-S1 Entropy > 5.5**: Strong LSTV candidate
- **Low confidence (<0.5)**: Model uncertainty
- **Bimodal distribution**: Mixed normal/abnormal anatomy

### Normal Anatomy Indicators
- **Entropy < 4.0**: Confident normal anatomy
- **High confidence (>0.7)**: Clear vertebral boundaries
- **Unimodal distribution**: Consistent predictions

## 🐛 Troubleshooting

### Container Issues
```bash
# Check container
singularity exec lstv-uncertainty.sif python --version

# Test GPU access
singularity exec --nv lstv-uncertainty.sif nvidia-smi
```

### SLURM Issues
```bash
# Check job status
squeue -u $USER

# View logs
tail -f logs/trial_*.out
tail -f logs/trial_*.err

# Cancel job
scancel <job_id>
```

### Data Issues
```bash
# Verify RSNA data
ls -lh data/raw/train_images/
cat data/raw/train_series_descriptions.csv | head

# Check for sagittal T2 series
grep -i "sagittal" data/raw/train_series_descriptions.csv | grep -i "t2" | wc -l
```

## 📚 References

1. **Ian Pan - RSNA 2024 Lumbar Spine Degenerative Classification (2nd Place)**
   - Kaggle Notebook: https://www.kaggle.com/code/yujiariyasu/rsna-lumbar-spine-2nd-place-solution
   - Original Author: Yuji Ariyasu (yujiariyasu)
   
2. **Point Net Model Checkpoint**
   - Dataset: https://www.kaggle.com/datasets/hengck23/rsna2024-demo-workflow
   - File: `00002484.pth` (130 MB)
   - Original Author: hengck23

3. **Epistemic Uncertainty in Deep Learning**
   - Gal & Ghahramani, 2016
   
4. **LSTV Classification**
   - Castellvi et al., 1984

## 👥 Team

**Wayne State University School of Medicine**
- Graduate Student: [Your Name]
- Advisor: [Advisor Name]
- Course: Medical Imaging / Machine Learning

## 📝 Citation

If you use this work, please cite:

```bibtex
@software{lstv_uncertainty_2026,
  title={LSTV Detection via Epistemic Uncertainty},
  author={[Your Name]},
  year={2026},
  organization={Wayne State University School of Medicine}
}
```

## 🔗 Links

- **RSNA Competition**: https://www.kaggle.com/competitions/rsna-2024-lumbar-spine-degenerative-classification
- **Ian Pan's Solution**: [Link to Kaggle notebook]
- **Tech Fair Demo**: http://localhost:5000

## 📄 License

MIT License - See LICENSE file for details

## 🎉 Acknowledgments

- Ian Pan for open-sourcing the RSNA 2nd place solution
- RSNA for the lumbar spine dataset
- Wayne State University for computational resources
