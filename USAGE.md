# LSTV Uncertainty Detection - Usage Guide

## Table of Contents
1. [Initial Setup](#initial-setup)
2. [Running on HPC Cluster](#running-on-hpc-cluster)
3. [Local Development](#local-development)
4. [Web Demo](#web-demo)
5. [Interpreting Results](#interpreting-results)
6. [Troubleshooting](#troubleshooting)

---

## Initial Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd lstv-uncertainty-detection
```

### 2. Build Docker Container (Local Machine)

**Automated build & push:**
```bash
cd docker
./build_and_push.sh
```

This script will:
- Build the container using PyTorch 2.3.1 with CUDA 12.1
- Test the container
- Ask for confirmation before pushing to Docker Hub
- Push to `go2432/lstv-uncertainty:latest`

**Manual build:**
```bash
cd docker
docker build -t go2432/lstv-uncertainty:latest .
docker push go2432/lstv-uncertainty:latest
```

### 3. Run Setup Script (On Cluster)
```bash
./setup.sh
```

This will:
- Create necessary directories
- Make scripts executable
- Check for required tools
- Provide next steps

---

## Running on HPC Cluster

### Option A: Complete Pipeline (Data Already Downloaded)

**Recommended if you already have RSNA data:**
```bash
sbatch slurm_scripts/00_master_pipeline_no_download.sh
```

This will:
1. Verify RSNA data exists
2. Run trial inference (10 studies)
3. Run production inference (all studies)
4. Generate reports

**Estimated time:** 6-8 hours
**Output:** `data/output/production/report.html`

### Option B: Complete Pipeline (Download + Process)

Run everything including data download:
```bash
sbatch slurm_scripts/00_master_pipeline.sh
```

This will:
1. Download RSNA dataset
2. Run trial inference (10 studies)
3. Run production inference (all studies)
4. Generate reports

**Estimated time:** 30-36 hours
**Output:** `data/output/production/report.html`

### Option C: Step-by-Step Execution

#### Step 1: Download Data
```bash
sbatch slurm_scripts/01_download_data.sh
```

**What it does:**
- Downloads RSNA 2024 Lumbar Spine dataset (~150 GB)
- Extracts DICOM files
- Organizes into `data/raw/`

**Time:** ~4-6 hours
**Check status:** `tail -f logs/download_*.out`

#### Step 1b: Download Model Checkpoint (Optional)
```bash
sbatch slurm_scripts/01b_download_model.sh
```

**What it does:**
- Downloads Point Net checkpoint from Kaggle
- File: `00002484.pth` from `hengck23/rsna2024-demo-workflow`
- Places at: `models/point_net_checkpoint.pth`

**Time:** ~5-10 minutes
**Size:** 130 MB
**Note:** If skipped, inference runs in MOCK mode

#### Step 2: Trial Run
```bash
sbatch slurm_scripts/02_trial_inference.sh
```

**What it does:**
- Processes 10 random studies
- Generates uncertainty metrics
- Creates HTML report

**Time:** ~30 minutes
**Output:** `data/output/trial/report.html`

#### Step 3: Production Run
```bash
sbatch slurm_scripts/03_prod_inference.sh
```

**What it does:**
- Processes all studies in dataset
- Calculates uncertainty for each vertebral level
- Generates comprehensive report

**Time:** ~4-6 hours
**Output:** `data/output/production/report.html`

### Option D: Debug Single Study

For detailed analysis of a specific study:
```bash
sbatch slurm_scripts/04_debug_single.sh <study_id>
```

Example:
```bash
sbatch slurm_scripts/04_debug_single.sh 123456789
```

**What it does:**
- Verbose logging
- Saves visualizations
- Generates detailed report

**Output:**
- `data/output/debug/report.html`
- `data/output/debug/debug_visualizations/`

---

## Local Development

### Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Download Sample Data

```bash
# Using Kaggle API
kaggle competitions download -c rsna-2024-lumbar-spine-degenerative-classification

# Extract
unzip rsna-2024-lumbar-spine-degenerative-classification.zip -d data/raw/
```

### Run Inference

#### Trial Mode (10 studies)
```bash
python src/inference.py \
    --input_dir data/raw/train_images \
    --series_csv data/raw/train_series_descriptions.csv \
    --output_dir data/output/trial \
    --mode trial
```

#### Debug Mode (1 study)
```bash
python src/inference.py \
    --input_dir data/raw/train_images \
    --series_csv data/raw/train_series_descriptions.csv \
    --output_dir data/output/debug \
    --mode debug \
    --debug_study_id 123456789
```

#### Production Mode (all studies)
```bash
python src/inference.py \
    --input_dir data/raw/train_images \
    --series_csv data/raw/train_series_descriptions.csv \
    --output_dir data/output/production \
    --mode prod
```

### Generate Report

```bash
python src/generate_report.py \
    --csv data/output/trial/lstv_uncertainty_metrics.csv \
    --output data/output/trial/report.html
```

With debug visualizations:
```bash
python src/generate_report.py \
    --csv data/output/debug/lstv_uncertainty_metrics.csv \
    --output data/output/debug/report.html \
    --debug_dir data/output/debug/debug_visualizations
```

---

## Web Demo

Perfect for tech fair demonstrations!

### Start Server

```bash
cd web
python app.py
```

Server starts at: `http://localhost:5000`

### Using the Demo

1. **Open Browser:** Navigate to `http://localhost:5000`
2. **Upload DICOM:** Drag & drop or click to browse
3. **Analyze:** Click "Analyze for LSTV"
4. **View Results:**
   - Risk level (HIGH/MEDIUM/LOW)
   - Uncertainty metrics per level
   - Visualization plots
   - Patient information

### Customize Demo

Edit `web/app.py` to:
- Change port: `app.run(port=8080)`
- Enable/disable debug: `debug=False`
- Modify risk thresholds
- Add custom visualizations

---

## Interpreting Results

### CSV Output

`lstv_uncertainty_metrics.csv` contains:

| Column | Description | Expected Range |
|--------|-------------|----------------|
| study_id | Unique study identifier | - |
| series_id | DICOM series ID | - |
| l1_l2_entropy | Shannon entropy for L1-L2 | 2.0-4.0 (normal) |
| l1_l2_confidence | Peak probability | 0.7-0.95 (normal) |
| ... | Same for all levels | ... |
| l5_s1_entropy | **KEY METRIC** | >5.0 suggests LSTV |
| l5_s1_confidence | L5-S1 peak probability | <0.5 suggests LSTV |

### HTML Report Sections

1. **Statistics Dashboard**
   - Total studies processed
   - High/Medium/Low risk counts
   - Detection rate

2. **Distribution Plots**
   - Entropy histograms per level
   - Expected: Bimodal for L5-S1 if LSTV present
   
3. **Top Candidates**
   - Ranked by L5-S1 entropy
   - Study IDs for further review
   
4. **Level Comparison**
   - Bar charts comparing all levels
   - L4-L5 and L5-S1 should show higher uncertainty

### Risk Levels

- **HIGH (Red):** Entropy > 5.5
  - Strong LSTV candidate
  - Recommend radiologist review
  
- **MEDIUM (Orange):** Entropy 4.0-5.5
  - Possible LSTV or borderline
  - Consider additional imaging
  
- **LOW (Green):** Entropy < 4.0
  - Likely normal anatomy
  - High model confidence

---

## Troubleshooting

### SLURM Issues

**Job won't start:**
```bash
# Check queue
squeue -u $USER

# Check job details
scontrol show job <job_id>

# Check available resources
sinfo
```

**Job failed:**
```bash
# View logs
tail -f logs/trial_*.err

# Common issues:
# - Out of memory: Increase --mem in SLURM script
# - GPU not available: Check --constraint setting
# - Time limit: Increase --time
```

**Cancel job:**
```bash
scancel <job_id>
```

### Container Issues

**Container not found:**
```bash
# Check cache
ls $HOME/singularity_cache/

# Pull manually
singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest
```

**GPU not accessible:**
```bash
# Test GPU in container
singularity exec --nv lstv-uncertainty.sif nvidia-smi

# If fails, check CUDA drivers
nvidia-smi
```

### Data Issues

**DICOM files not found:**
```bash
# Verify directory structure
ls -lh data/raw/train_images/

# Check series CSV
head -20 data/raw/train_series_descriptions.csv
```

**Series CSV missing:**
```bash
# Re-download
cd data/raw
kaggle competitions download -c rsna-2024-lumbar-spine-degenerative-classification
unzip train_series_descriptions.csv.zip
```

### Python Issues

**Import errors:**
```bash
# Verify environment
which python
pip list | grep pydicom

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**CUDA errors:**
```bash
# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# If False, reinstall PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Web Demo Issues

**Port already in use:**
```bash
# Change port in app.py
app.run(port=5001)

# Or kill existing process
lsof -ti:5000 | xargs kill -9
```

**Upload fails:**
```bash
# Check file size limit in app.py
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Verify DICOM file
pydicom-show <file.dcm>
```

---

## Getting Help

### Check Logs

```bash
# SLURM output
tail -f logs/trial_*.out

# SLURM errors
tail -f logs/trial_*.err

# Python logs (if using logging)
tail -f inference.log
```

### Verify Setup

```bash
# Run setup again
./setup.sh

# Check configuration
cat config/config.json

# Test container
singularity exec lstv-uncertainty.sif python --version
```

### Contact

For issues or questions:
- Email: go2432@wayne.edu
- GitHub Issues: [Repository URL]
- Office Hours: [Times/Location]

---

## Best Practices

1. **Start Small:** Always run trial mode first
2. **Check Outputs:** Verify CSV and HTML before full run
3. **Monitor Resources:** Watch memory/GPU usage
4. **Save Results:** Copy reports before re-running
5. **Document Changes:** Keep notes on parameter modifications

---

## Quick Reference

### Essential Commands

```bash
# Complete pipeline
sbatch slurm_scripts/00_master_pipeline.sh

# Trial run
sbatch slurm_scripts/02_trial_inference.sh

# Check status
squeue -u $USER

# View report
firefox data/output/trial/report.html

# Start web demo
cd web && python app.py
```

### Important Paths

- **Data:** `data/raw/train_images/`
- **Results:** `data/output/`
- **Logs:** `logs/`
- **Models:** `models/`
- **Container:** `$HOME/singularity_cache/`

### Key Files

- **Inference:** `src/inference.py`
- **Report:** `src/generate_report.py`
- **Web Demo:** `web/app.py`
- **Config:** `config/config.json`
