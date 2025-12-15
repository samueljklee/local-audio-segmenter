# Local Audio Segmenter - UV Environment Setup

## 🚀 **UV Environment is Ready!**

The Local Audio Segmenter is fully configured to work with the **uv** package manager and environment manager.

## 📦 **Quick Start with UV**

### Activate the Environment
```bash
# If you just cloned this project
uv sync

# The environment is ready to use!
```

### Run the Audio Segmenter
```bash
# Basic segmentation
uv run python -m src.cli.main audio.wav

# With transcription (uses local Whisper)
uv run python -m src.cli.main audio.wav --transcribe

# With specific Whisper model
uv run python -m src.cli.main audio.wav --transcribe --whisper-model small

# Using configuration profiles
uv run python -m src.cli.main sermon.wav --profile church_service --transcribe
uv run python -m src.cli.main lecture.mp3 --profile lecture --transcribe

# Export to JSON for analysis
uv run python -m src.cli.main audio.wav --transcribe --export-format json

# Advanced options
uv run python -m src.cli.main audio.wav \
  --transcribe \
  --whisper-model base \
  --export-format json \
  --profile podcast
```

## 🎯 **UV Benefits**

### ✅ **Performance**
- **Much faster** than pip installation
- Parallel downloads and builds
- Efficient caching

### ✅ **Dependency Management**
- Isolated virtual environment (`.venv`)
- Reproducible builds with `uv.lock`
- Compatible with pip when needed

### ✅ **Development**
```bash
# Add development dependencies
uv add --dev pytest black mypy

# Run code formatting
uv run black .

# Run type checking
uv run mypy src/

# Run tests
uv run pytest
```

## 🛠️ **Development Setup**

### Install Development Dependencies
```bash
uv sync --dev
```

### Available Commands
```bash
# Code formatting
uv run black src/

# Type checking
uv run mypy src/

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src

# Run linting
uv run flake8 src/
```

## 📋 **Project Structure**

```
audio-auto-segmentation/
├── .venv/                 # UV virtual environment
├── uv.lock              # Locked dependencies
├── pyproject.toml       # Project configuration
├── src/                 # Source code
│   ├── cli/             # Command-line interface
│   ├── core/            # Core pipeline
│   ├── stt/             # Speech-to-text module
│   ├── config/          # Configuration management
│   ├── detection/       # Audio detection algorithms
│   ├── semantic/        # Semantic labeling
│   ├── audio/           # Audio processing
│   └── segmentation/    # Segmentation algorithms
├── tests/               # Test suite
└── README_UV.md         # This file
```

## 🔧 **Environment Variables**

The UV environment includes all required dependencies:

### Core Dependencies
- **librosa** - Audio processing
- **numpy**, **scipy** - Numerical computing
- **whisper** - Local speech-to-text
- **soundfile** - Audio I/O
- **PyYAML** - Configuration parsing
- **click** - CLI interface

### Machine Learning
- **torch** - Deep learning (Whisper backend)
- **scikit-learn** - ML algorithms
- **librosa** - Audio feature extraction

### Development Tools
- **pytest** - Testing framework
- **black** - Code formatting
- **mypy** - Type checking
- **coverage** - Test coverage

## 🎯 **Performance with UV**

- **Installation**: ~10-15 seconds (vs 2-3 minutes with pip)
- **Startup**: Instant with cached dependencies
- **Memory**: Efficient isolated environment
- **Compatibility**: Full pip compatibility

## 🚨 **Troubleshooting**

### If UV is not installed:
```bash
# Install uv (curl method)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip (slower)
pip install uv
```

### If environment issues:
```bash
# Recreate environment
rm -rf .venv
uv sync

# Check environment
uv run python --version
```

### If dependencies fail:
```bash
# Force refresh
uv sync --refresh

# Clear cache
uv cache clean
```

## 🎉 **Ready to Use!**

The UV environment is fully configured and ready for:

- ✅ Local audio segmentation
- ✅ Whisper speech-to-text transcription
- ✅ Configuration profiles (church, lecture, podcast, meeting)
- ✅ JSON/CSV/TXT export formats
- ✅ Command-line interface
- ✅ Development and testing

**Start processing audio locally with uv today!** 🚀