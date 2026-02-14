#!/bin/bash
# Quick setup script for LSTV Uncertainty Detection

set -e

echo "================================================================"
echo "LSTV Uncertainty Detection - Setup Script"
echo "================================================================"

# Check if on cluster
if command -v sbatch &> /dev/null; then
    ON_CLUSTER=true
    echo "✓ Detected SLURM cluster environment"
else
    ON_CLUSTER=false
    echo "ℹ Running in local environment"
fi

# Create directories
echo ""
echo "Creating directory structure..."
mkdir -p data/{raw,output} models logs

# Make scripts executable
echo "Making scripts executable..."
chmod +x slurm_scripts/*.sh
chmod +x src/*.py
chmod +x web/app.py

if [ "$ON_CLUSTER" = true ]; then
    echo ""
    echo "================================================================"
    echo "HPC CLUSTER SETUP"
    echo "================================================================"
    
    # Check for Kaggle credentials
    if [ ! -f "$HOME/.kaggle/kaggle.json" ]; then
        echo ""
        echo "⚠️  Kaggle credentials not found!"
        echo ""
        echo "Setup instructions:"
        echo "  1. Go to: https://www.kaggle.com/settings/account"
        echo "  2. Click 'Create New Token' under API section"
        echo "  3. Save kaggle.json to ~/.kaggle/"
        echo "  4. Run: chmod 600 ~/.kaggle/kaggle.json"
        echo ""
    else
        echo "✓ Kaggle credentials found"
    fi
    
    # Check for Singularity
    if command -v singularity &> /dev/null; then
        echo "✓ Singularity found: $(singularity --version)"
    else
        echo "⚠️  Singularity not found"
    fi
    
    # Setup Singularity cache
    export NXF_SINGULARITY_CACHEDIR="${HOME}/singularity_cache"
    mkdir -p $NXF_SINGULARITY_CACHEDIR
    echo "✓ Singularity cache: $NXF_SINGULARITY_CACHEDIR"
    
    echo ""
    echo "================================================================"
    echo "NEXT STEPS"
    echo "================================================================"
    echo ""
    echo "1. Verify Kaggle credentials are set up"
    echo "2. Run the master pipeline:"
    echo "   sbatch slurm_scripts/00_master_pipeline.sh"
    echo ""
    echo "OR run individual steps:"
    echo "   sbatch slurm_scripts/01_download_data.sh"
    echo "   sbatch slurm_scripts/02_trial_inference.sh"
    echo "   sbatch slurm_scripts/03_prod_inference.sh"
    echo ""
    echo "To debug a single study:"
    echo "   sbatch slurm_scripts/04_debug_single.sh <study_id>"
    echo ""
    
else
    echo ""
    echo "================================================================"
    echo "LOCAL ENVIRONMENT SETUP"
    echo "================================================================"
    
    # Check for Python
    if command -v python3 &> /dev/null; then
        echo "✓ Python found: $(python3 --version)"
    else
        echo "✗ Python not found"
        exit 1
    fi
    
    # Check for Docker
    if command -v docker &> /dev/null; then
        echo "✓ Docker found: $(docker --version)"
    else
        echo "⚠️  Docker not found (optional)"
    fi
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo ""
        echo "Creating virtual environment..."
        python3 -m venv venv
        echo "✓ Virtual environment created"
    fi
    
    echo ""
    echo "================================================================"
    echo "NEXT STEPS"
    echo "================================================================"
    echo ""
    echo "1. Activate virtual environment:"
    echo "   source venv/bin/activate"
    echo ""
    echo "2. Install dependencies:"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "3. Run trial inference:"
    echo "   python src/inference.py \\"
    echo "     --input_dir data/raw/train_images \\"
    echo "     --series_csv data/raw/train_series_descriptions.csv \\"
    echo "     --output_dir data/output/trial \\"
    echo "     --mode trial"
    echo ""
    echo "4. Generate report:"
    echo "   python src/generate_report.py \\"
    echo "     --csv data/output/trial/lstv_uncertainty_metrics.csv \\"
    echo "     --output data/output/trial/report.html"
    echo ""
    echo "5. Run web demo:"
    echo "   cd web && python app.py"
    echo ""
fi

echo "================================================================"
echo "Setup complete!"
echo "================================================================"
