FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

# Metadata
LABEL maintainer="go2432@wayne.edu"
LABEL description="LSTV Detection via Epistemic Uncertainty"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    git \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Using python-gdcm and pylibjpeg for DICOM support (much faster than conda)
RUN pip install --no-cache-dir \
    python-gdcm \
    pylibjpeg \
    pylibjpeg-libjpeg \
    pydicom==2.4.4 \
    nibabel==5.2.0 \
    timm==0.9.10 \
    albumentations==1.3.1 \
    opencv-python-headless==4.8.1.78 \
    scikit-learn==1.3.2 \
    pandas==2.1.4 \
    matplotlib==3.8.2 \
    seaborn==0.13.0 \
    tqdm==4.66.1 \
    jinja2==3.1.2 \
    plotly==5.18.0 \
    scipy==1.11.4 \
    natsort==8.4.0 \
    loguru==0.7.2 \
    kaggle==1.5.16 \
    flask==3.0.0

# Create working directories
RUN mkdir -p /work /data/input /data/output /app/models

WORKDIR /work

# Default command
CMD ["/bin/bash"]
