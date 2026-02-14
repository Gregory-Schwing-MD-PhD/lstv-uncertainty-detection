# 🚀 QUICK START - LSTV Uncertainty Detection

## Get Started in 3 Steps

### 1️⃣ Clone & Setup
```bash
git clone <your-repo-url>
cd lstv-uncertainty-detection
./setup.sh

# Build and push Docker container (on local machine)
cd docker
./build_and_push.sh
cd ..
```

### 2️⃣ Run on Cluster
```bash
# If data already downloaded (recommended)
sbatch slurm_scripts/00_master_pipeline_no_download.sh

# OR complete pipeline (downloads data + model)
sbatch slurm_scripts/00_master_pipeline.sh

# OR step-by-step
sbatch slurm_scripts/01_download_data.sh     # Download RSNA data
sbatch slurm_scripts/01b_download_model.sh   # Download model checkpoint
sbatch slurm_scripts/02_trial_inference.sh   # Trial run
sbatch slurm_scripts/03_prod_inference.sh    # Full dataset
```

### 3️⃣ View Results
```bash
firefox data/output/production/report.html
```

---

## 🐳 Docker Container

### Build & Push (Local Machine)
```bash
cd docker
./build_and_push.sh
```

This will:
- Build: `go2432/lstv-uncertainty:latest`
- Test the container
- Push to Docker Hub

**Manual build:**
```bash
docker build -t go2432/lstv-uncertainty:latest .
docker push go2432/lstv-uncertainty:latest
```

---

## 🎯 What This Does

**Novel Approach:** Uses epistemic uncertainty from Ian Pan's RSNA spine localizer to detect LSTV

**How:** Models trained on normal anatomy show high confusion when they encounter abnormal anatomy

**Output:** 
- CSV with uncertainty metrics per study
- Interactive HTML report with risk stratification
- Top LSTV candidates ranked by uncertainty

---

## 📊 Expected Results

- **15-30% LSTV Detection Rate** (matches literature)
- **L5-S1 Entropy > 5.0** = High risk
- **Bimodal Distribution** = Clear separation

---

## 🖥️ Tech Fair Demo

```bash
cd web
python app.py
```

Open: `http://localhost:5000`

Upload DICOM → Get instant LSTV risk assessment!

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `docker/build_and_push.sh` | Build & push container |
| `src/inference.py` | Main inference pipeline |
| `src/generate_report.py` | HTML report generator |
| `web/app.py` | Interactive demo |
| `slurm_scripts/00_master_pipeline_no_download.sh` | Run if data downloaded |
| `slurm_scripts/00_master_pipeline.sh` | Full pipeline + download |
| `slurm_scripts/01b_download_model.sh` | Download Point Net checkpoint |

---

## 🆘 Quick Help

**Check job status:**
```bash
squeue -u $USER
```

**View logs:**
```bash
tail -f logs/trial_*.out
```

**Debug single study:**
```bash
sbatch slurm_scripts/04_debug_single.sh <study_id>
```

**Pull container on cluster:**
```bash
singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest
```

---

## 📚 Documentation

- **Full Guide:** `README.md`
- **Detailed Usage:** `USAGE.md`
- **Configuration:** `config/config.json`

---

## 🎓 Citation

```bibtex
@software{lstv_uncertainty_2026,
  title={LSTV Detection via Epistemic Uncertainty},
  author={Wayne State University School of Medicine},
  year={2026},
  url={https://github.com/your-repo}
}
```

---

**Questions?** Email: go2432@wayne.edu
