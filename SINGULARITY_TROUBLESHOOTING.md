# Singularity/Apptainer Troubleshooting Guide

## Common Singularity Errors and Fixes

### 1. "Read-only file system" Errors

**Error:**
```
ERROR: cannot create file '/tmp/something': Read-only file system
```

**Cause:** Singularity containers are read-only by default. Writing to paths inside the container (like `/tmp`) fails.

**Fix:** All our scripts avoid this by:
```bash
# ✓ GOOD - Write to bound project directory
singularity exec --bind $PROJECT_DIR:/work "$IMG" bash -c "cd /work && command"

# ✗ BAD - Try to write to container's /tmp
singularity exec "$IMG" bash -c "cd /tmp && command"
```

**Verification:** Check that scripts use `/work` for all operations:
```bash
grep -r "/tmp" slurm_scripts/  # Should return nothing
grep -r "/work" slurm_scripts/ # Should show all operations
```

---

### 2. "File not found" After Writing

**Error:**
```
Created file in container, but not found on host
```

**Cause:** File was written inside container's overlay, not to bound mount.

**Fix:** Ensure paths are relative to bound mount:
```bash
# ✓ GOOD - File appears on host
--bind $PROJECT_DIR:/work
cd /work/models/
echo "test" > file.txt  # Appears at $PROJECT_DIR/models/file.txt

# ✗ BAD - File disappears after container exits
cd /models/
echo "test" > file.txt  # Only exists in container overlay
```

---

### 3. Kaggle/Model Downloads Fail

**Error:**
```
kaggle: cannot create directory: Read-only file system
```

**Fix:** Our scripts handle this correctly:
```bash
# Create temp dir in writable project space
TMP_DIR="${PROJECT_DIR}/.tmp_download"
mkdir -p "$TMP_DIR"

# Download there, not to container's /tmp
singularity exec --bind $PROJECT_DIR:/work "$IMG" bash -c "
    cd /work/.tmp_download
    kaggle datasets download ...
    unzip ...
    mv file /work/models/
"
```

---

### 4. "Permission denied" on Bind Mounts

**Error:**
```
FATAL: could not bind /path/to/dir: permission denied
```

**Cause:** Trying to bind a directory you don't have permission to read/write.

**Fix:** Use directories you own:
```bash
# ✓ GOOD - Your home directory and subdirs
--bind $HOME/project:/work

# ✗ BAD - System directories
--bind /data/shared:/data  # Might not have permission
```

**Our approach:** Everything under `$PROJECT_DIR` which you always own.

---

### 5. "No space left on device" in /tmp

**Error:**
```
ERROR: no space left on device: /tmp/...
```

**Cause:** Container's `/tmp` is in overlay filesystem with limited space.

**Fix:** Use project directory for temp files:
```bash
# Set temp directory
export SINGULARITY_TMPDIR="${PROJECT_DIR}/.tmp_singularity"
mkdir -p "$SINGULARITY_TMPDIR"

# This is already in all SLURM scripts:
export SINGULARITY_TMPDIR="/tmp/${USER}_job_${SLURM_JOB_ID}"
mkdir -p "$SINGULARITY_TMPDIR"
trap 'rm -rf "$SINGULARITY_TMPDIR"' EXIT
```

---

### 6. Model Loading Fails Inside Container

**Error:**
```
RuntimeError: Can't load /app/models/checkpoint.pth
```

**Cause:** Model checkpoint not in bound path.

**Fix:** Bind models directory and use bound path:
```bash
# ✓ GOOD
--bind $PROJECT_DIR:/work
python script.py --checkpoint /work/models/point_net_checkpoint.pth

# ✗ BAD
python script.py --checkpoint /app/models/point_net_checkpoint.pth  # Not bound
```

---

### 7. Environment Variables Not Set

**Error:**
```
WANDB_DIR not found, using /tmp (read-only error)
```

**Fix:** Pass environment variables and ensure they point to writable locations:
```bash
singularity exec \
    --bind $PROJECT_DIR:/work \
    --env WANDB_DIR=/work/wandb \
    --env WANDB_API_KEY=$WANDB_API_KEY \
    "$IMG" python train.py
```

Our scripts already do this for all necessary env vars.

---

## How Our Scripts Avoid These Issues

### Principle: Everything in Project Directory

```
project/
├── data/raw/           ← Bound to /work/data/raw
├── data/output/        ← Bound to /work/data/output  
├── models/             ← Bound to /work/models
├── .tmp_download/      ← Bound to /work/.tmp_download
├── .tmp_singularity/   ← Used for SINGULARITY_TMPDIR
└── logs/               ← SLURM logs (on host)
```

### Standard Bind Pattern

Every script uses:
```bash
singularity exec \
    --bind $PROJECT_DIR:/work \     # Entire project is /work
    --pwd /work \                    # Start in /work
    "$IMG" \
    bash -c "
        cd /work/.tmp_download       # Work in project space
        do_something                 # All writes to /work/*
        mv result /work/output/      # Result in project space
    "
```

### Cleanup Pattern

Every script cleans up temp files:
```bash
cleanup() {
    rm -rf "$TMP_DIR"
    rm -rf ${PROJECT_DIR}/.kaggle_tmp
    rm -rf "$SINGULARITY_TMPDIR"
}
trap cleanup EXIT
```

---

## Debugging Checklist

If you get read-only errors:

1. **Check bind mounts:**
   ```bash
   # Should show: /work
   singularity exec --bind $PROJECT_DIR:/work "$IMG" pwd
   ```

2. **Verify write permissions:**
   ```bash
   singularity exec --bind $PROJECT_DIR:/work "$IMG" bash -c "touch /work/test.txt && rm /work/test.txt"
   ```

3. **Check temp directory:**
   ```bash
   echo $SINGULARITY_TMPDIR  # Should be in project or /tmp/$USER_$JOBID
   ls -ld $SINGULARITY_TMPDIR  # Should exist and be writable
   ```

4. **Verify all operations in /work:**
   ```bash
   # In script, replace:
   cd /tmp  → cd /work/.tmp_download
   /models/ → /work/models/
   /data/   → /work/data/
   ```

5. **Check SLURM logs:**
   ```bash
   tail -50 logs/trial_*.err  # Look for "Read-only" or "Permission denied"
   ```

---

## Quick Fixes

### Fix 1: Download Script Fails
```bash
# Make sure temp dir exists
mkdir -p .tmp_download
chmod 755 .tmp_download

# Re-run
sbatch slurm_scripts/01_download_data.sh
```

### Fix 2: Model Download Fails
```bash
# Make sure models dir exists
mkdir -p models
chmod 755 models

# Re-run
sbatch slurm_scripts/01b_download_model.sh
```

### Fix 3: Inference Fails
```bash
# Check model exists in writable location
ls -lh models/point_net_checkpoint.pth

# Check data exists
ls -lh data/raw/train_images/ | head

# Re-run
sbatch slurm_scripts/02_trial_inference.sh
```

---

## Still Having Issues?

1. **Test basic container access:**
   ```bash
   singularity exec --bind $PWD:/work lstv-uncertainty.sif python --version
   ```

2. **Test write access:**
   ```bash
   singularity exec --bind $PWD:/work lstv-uncertainty.sif bash -c "echo test > /work/test.txt && cat /work/test.txt"
   ```

3. **Check container is valid:**
   ```bash
   singularity inspect lstv-uncertainty.sif
   ```

4. **Rebuild container:**
   ```bash
   rm lstv-uncertainty.sif
   singularity pull lstv-uncertainty.sif docker://go2432/lstv-uncertainty:latest
   ```

5. **Check cluster-specific settings:**
   ```bash
   # Some clusters need:
   export SINGULARITY_BIND="$PWD:/work"
   # or
   export APPTAINER_BIND="$PWD:/work"
   ```

---

## Prevention Best Practices

1. ✅ Always bind project directory as `/work`
2. ✅ All file operations relative to `/work`
3. ✅ Set `SINGULARITY_TMPDIR` to writable location
4. ✅ Clean up temp directories on exit
5. ✅ Use `--pwd /work` to start in writable directory
6. ✅ Pass environment variables with `--env`
7. ✅ Test with simple commands before full runs

---

**Bottom line:** If everything stays under `$PROJECT_DIR` and is bound to `/work`, you won't have read-only issues!
