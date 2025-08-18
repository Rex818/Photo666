# Photo666 v0.3.0 - Simple Installation Guide

## Quick Start (Windows)

### Step 1: Extract and Navigate
1. Extract `Photo666-v0.3.0.zip` to a folder
2. Open PowerShell in that folder
3. Run: `.\start.bat`

### Step 2: If start.bat fails, manual installation:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (English version, no encoding issues)
pip install -r requirements.txt

# Run the program
python main.py
```

## Alternative Installation Methods

### Method 1: Install PyTorch separately (Recommended for GPU users)
```powershell
# First install PyTorch with CUDA support
pip install torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128 --index-url https://download.pytorch.org/whl/cu128

# Then install other dependencies
pip install PyQt6>=6.5.0 Pillow>=10.2.0 PyYAML>=6.0.0 sqlite-utils>=3.35.0 googletrans-py>=4.0.0 asyncio-mqtt>=0.11.0 aiofiles>=22.0.0 transformers>=4.55.0 huggingface_hub>=0.16.0 accelerate>=1.9.0 safetensors>=0.3.0 bitsandbytes>=0.41.0 numpy>=1.24.0 einops>=0.8.0 timm>=1.0.0 requests>=2.28.0 geopy>=2.3.0 tqdm>=4.60.0
```

### Method 2: Use conda (Alternative)
```bash
# Install PyTorch with CUDA
conda install pytorch torchvision torchaudio pytorch-cuda=12.8 -c pytorch -c nvidia

# Install other dependencies
pip install PyQt6>=6.5.0 Pillow>=10.2.0 PyYAML>=6.0.0 sqlite-utils>=3.35.0 googletrans-py>=4.0.0 asyncio-mqtt>=0.11.0 aiofiles>=22.0.0 transformers>=4.55.0 huggingface_hub>=0.16.0 accelerate>=1.9.0 safetensors>=0.3.0 bitsandbytes>=0.41.0 numpy>=1.24.0 einops>=0.8.0 timm>=1.0.0 requests>=2.28.0 geopy>=2.3.0 tqdm>=4.60.0
```

## Troubleshooting

### Encoding Error (UnicodeDecodeError)
- **Problem**: `'gbk' codec can't decode byte 0xae`
- **Solution**: Use the English `requirements.txt` file (already fixed)
- **Alternative**: Use Method 1 or 2 above

### PyTorch Installation Issues
- **Problem**: CUDA version not compatible
- **Solution**: Use the official PyTorch command from Method 1
- **Alternative**: Use conda installation from Method 2

### Virtual Environment Issues
- **Problem**: Cannot activate virtual environment
- **Solution**: Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell as Administrator

## System Requirements

- **OS**: Windows 10/11
- **Python**: 3.8+
- **RAM**: 8GB+ (16GB recommended)
- **Storage**: 2GB+
- **GPU**: NVIDIA with CUDA 12.8+ (optional, for AI acceleration)

## Support

If you encounter issues:
1. Check the logs in `logs/picman.log`
2. Refer to `INSTALL.md` for detailed instructions
3. Check `RELEASE_README.md` for version information
