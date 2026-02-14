# Docker Build Optimization - Technical Notes

## Why We Removed Conda

### The Problem with Conda in PyTorch Images

The `pytorch/pytorch` base images come with a pre-configured Python environment. When you add `conda install`, you get:

1. **Slow Builds** ⏱️
   - Conda has to solve the entire dependency graph
   - Downloads massive metadata files
   - Can take 5-10 minutes just for GDCM

2. **Large Images** 📦
   - Conda downloads its own package cache
   - Duplicate dependencies (pip vs conda)
   - Final image can be 1-2 GB larger

3. **Dependency Conflicts** ⚠️
   - Conda may try to downgrade PyTorch
   - "Diamond dependency" problems
   - Conflicts between pip and conda packages

### The Solution: pip + apt

We replaced:
```dockerfile
# OLD (Slow)
RUN conda install -c conda-forge gdcm -y && \
    conda clean -a -y
```

With:
```dockerfile
# NEW (Fast)
RUN pip install --no-cache-dir \
    python-gdcm \
    pylibjpeg \
    pylibjpeg-libjpeg
```

## GDCM Alternatives

### What is GDCM?
GDCM (Grassroots DICOM) is a C++ library for reading compressed DICOM files. Medical images often use JPEG compression to save space.

### Option 1: python-gdcm (Our Choice)
```bash
pip install python-gdcm
```

**Pros:**
- ✅ Pip-installable binary wheel
- ✅ Fast installation (~10 seconds)
- ✅ Full GDCM functionality
- ✅ Works with pydicom automatically

**Cons:**
- ⚠️ May not be available for all platforms
- ⚠️ Sometimes lags behind latest GDCM

### Option 2: pylibjpeg (Backup)
```bash
pip install pylibjpeg pylibjpeg-libjpeg
```

**Pros:**
- ✅ Pure Python + wheels
- ✅ Very fast
- ✅ Handles most JPEG-compressed DICOMs
- ✅ Actively maintained

**Cons:**
- ⚠️ Doesn't handle all GDCM codecs
- ⚠️ May not work for exotic compression

### Option 3: Both (Belt + Suspenders)
```bash
pip install python-gdcm pylibjpeg pylibjpeg-libjpeg
```

**Our approach:**
- Try python-gdcm first
- Fall back to pylibjpeg if needed
- Log which decoder is being used

## Code Implementation

### In inference.py

```python
# Enable GDCM for compressed DICOM support
try:
    import gdcm
    pydicom.config.use_gdcm = True
    logger.info("Using GDCM for DICOM decompression")
except ImportError:
    logger.warning("GDCM not available, using pydicom default decoders")
    # Fallback to pylibjpeg if available
    try:
        import pylibjpeg
        logger.info("Using pylibjpeg for DICOM decompression")
    except ImportError:
        logger.warning("Neither GDCM nor pylibjpeg available - compressed DICOMs may fail")
```

This gives us:
1. Try GDCM first (most compatible)
2. Fall back to pylibjpeg (fast, pure Python)
3. Log which one is being used
4. Graceful degradation if neither available

## Build Time Comparison

### Before (With Conda):
```
Step 1/10 : FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime
 ---> 100% [===============================================] 2.5GB/2.5GB
Step 5/10 : RUN conda install -c conda-forge gdcm -y
 ---> Running in abc123...
Collecting package metadata (current_repodata.json): ...done
Solving environment: ...done
[5-10 minutes]
 ---> Image size: ~5.2 GB
```

### After (Pip Only):
```
Step 1/10 : FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime
 ---> 100% [===============================================] 2.5GB/2.5GB
Step 5/10 : RUN pip install python-gdcm pylibjpeg pylibjpeg-libjpeg
 ---> Running in xyz789...
Collecting python-gdcm
  Downloading python_gdcm-3.0.24.1-py3-none-manylinux2014_x86_64.whl (5.2 MB)
[10-30 seconds]
 ---> Image size: ~3.2 GB
```

**Improvement:**
- ⚡ ~10x faster build
- 📦 ~2 GB smaller image
- 🎯 More reliable (no conda solver)

## Testing DICOM Support

### Test if GDCM is working:
```python
import pydicom

# Try to read a compressed DICOM
dcm = pydicom.dcmread('compressed_image.dcm')
print(f"Transfer Syntax: {dcm.file_meta.TransferSyntaxUID}")
print(f"Pixel Data Shape: {dcm.pixel_array.shape}")
```

### Common Transfer Syntaxes:
- `1.2.840.10008.1.2.4.50` - JPEG Baseline (needs GDCM/pylibjpeg)
- `1.2.840.10008.1.2.4.70` - JPEG Lossless (needs GDCM/pylibjpeg)
- `1.2.840.10008.1.2.4.90` - JPEG 2000 (needs GDCM)
- `1.2.840.10008.1.2` - Implicit VR Little Endian (native pydicom)

### If you get errors:
```
NotImplementedError: Unable to decode pixel data with a transfer syntax UID of ...
```

**Fix:**
1. Check `python-gdcm` is installed: `pip list | grep gdcm`
2. Check `pylibjpeg` is installed: `pip list | grep pylibjpeg`
3. Enable in pydicom: `pydicom.config.use_gdcm = True`

## Fallback Strategy

If `python-gdcm` fails to install:

### Option A: Use pylibjpeg only
```dockerfile
RUN pip install --no-cache-dir \
    pylibjpeg \
    pylibjpeg-libjpeg \
    pylibjpeg-openjpeg \
    pylibjpeg-rle
```

### Option B: Build GDCM from source
```dockerfile
RUN apt-get update && apt-get install -y \
    cmake \
    libexpat1-dev \
    swig \
    && git clone https://github.com/malaterre/GDCM.git \
    && cd GDCM \
    && mkdir build && cd build \
    && cmake -DGDCM_BUILD_SHARED_LIBS=ON -DGDCM_WRAP_PYTHON=ON .. \
    && make -j$(nproc) \
    && make install
```

### Option C: Use pre-compiled wheel
```dockerfile
RUN pip install --no-cache-dir \
    https://github.com/pydicom/python-gdcm/releases/download/v3.0.24.1/python_gdcm-3.0.24.1-cp310-cp310-manylinux_2_17_x86_64.whl
```

## Verification Checklist

After building the container:

```bash
# Build container
docker build -t go2432/lstv-uncertainty:latest .

# Test Python imports
docker run --rm go2432/lstv-uncertainty:latest python -c "import gdcm; print('GDCM OK')"
docker run --rm go2432/lstv-uncertainty:latest python -c "import pylibjpeg; print('pylibjpeg OK')"

# Test pydicom
docker run --rm go2432/lstv-uncertainty:latest python -c "
import pydicom
print(f'pydicom version: {pydicom.__version__}')
print(f'GDCM enabled: {pydicom.config.use_gdcm}')
"

# Check image size
docker images | grep lstv-uncertainty
```

**Expected output:**
- GDCM OK ✅
- pylibjpeg OK ✅
- Image size: ~3-4 GB ✅
- Build time: <2 minutes ✅

## Troubleshooting

### Issue: `python-gdcm` not found
**Try:**
```bash
pip install python-gdcm --no-binary :all:  # Force build from source
```

### Issue: Import error for `gdcm`
**Check Python version:**
```bash
python --version  # Should be 3.10
```

`python-gdcm` wheels are only available for specific Python versions.

### Issue: Still slow builds
**Clear Docker cache:**
```bash
docker builder prune -a
docker build --no-cache -t go2432/lstv-uncertainty:latest .
```

## Summary

✅ **Use pip instead of conda**
✅ **Install python-gdcm + pylibjpeg**
✅ **Enable GDCM in code with fallback**
✅ **Test with compressed DICOMs**

Result: Faster builds, smaller images, fewer conflicts! 🎉
