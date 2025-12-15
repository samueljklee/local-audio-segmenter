# Testing Guide for Local Audio Segmenter

## 🧪 **Honest Assessment & Testing Guide**

### ✅ **What's Confirmed Working:**

1. **Core Infrastructure**: ✅
   - All modules load correctly
   - CLI interface complete with all options
   - Whisper model installation and loading
   - Audio processing pipeline

2. **Basic Segmentation**: ✅
   - Can detect 2-3 segments in test audio
   - Processing time: ~1-2 seconds
   - Memory management works

### ❌ **Known Limitations:**

1. **Speech Detection**: ❌ **Weak**
   - Synthetic speech patterns get classified as music
   - Real speech detection needs tuning
   - Detection confidence thresholds may need adjustment

2. **Real-World Testing**: ❌ **Not Done**
   - Haven't tested with actual human speech recordings
   - Transcription quality unknown with real audio

## 🎯 **How to Properly Test:**

### Option 1: Use Real Audio Files

**Recommended sources for test audio:**

1. **LibriVox** (free public domain audiobooks):
   ```bash
   # Download a short clip
   curl -o test_speech.mp3 "https://www.archive.org/download/alices_adventures_0107_librivox/alices_adventures_01_carroll_64kb.mp3"

   # Test it
   python3 -m src.cli.main test_speech.mp3 --transcribe
   ```

2. **Common Voice Dataset** (Mozilla):
   ```bash
   # Download samples (requires account)
   # Test with real speech recordings
   ```

3. **Your own recordings**:
   ```bash
   # Record with your phone/computer
   # Save as .wav or .mp3
   python3 -m src.cli.main your_recording.wav --transcribe
   ```

### Option 2: Test Different Scenarios

```bash
# Basic segmentation
python3 -m src.cli.main audio.wav

# With transcription
python3 -m src.cli.main audio.wav --transcribe

# Different Whisper models (more accurate but slower)
python3 -m src.cli.main audio.wav --transcribe --whisper-model small
python3 -m src.cli.main audio.wav --transcribe --whisper-model base

# Export to JSON for detailed analysis
python3 -m src.cli.main audio.wav --transcribe --export-format json

# With specific language
python3 -m src.cli.main audio.wav --transcribe --transcription-language en

# Check only speech detection
python3 -m src.cli.main audio.wav --speech-only --no-semantic

# Use church service profile
python3 -m src.cli.main sermon.wav --profile church_service --transcribe
```

### Option 3: Validate Components Separately

```bash
# Test CLI help (should show all options)
python3 -m src.cli.main --help | grep transcribe

# Test Whisper model loading
python3 -c "from src.stt.module import STTModule; stt = STTModule('tiny'); print('✅ Whisper loaded'); stt.cleanup()"

# Test configuration loading
python3 -c "from src.config.settings import ConfigManager; cfg = ConfigManager('church_service'); print('✅ Church profile loaded')"
```

## 🎯 **Expected Results:**

**Good audio should produce:**
- 2-10 segments detected
- Transcription text (if speech present)
- Processing time < 10 seconds for < 5 minute audio
- JSON output with segment details

**Poor audio may produce:**
- Everything classified as music or silence
- Empty transcription
- Very low confidence scores

## 🐛 **Troubleshooting:**

### If transcription fails:
```bash
# Check Whisper installation
python3 -c "import whisper; print(whisper.__version__)"

# Test with tiny model first
python3 -m src.cli.main audio.wav --transcribe --whisper-model tiny
```

### If segmentation seems wrong:
```bash
# Try different thresholds
python3 -m src.cli.main audio.wav --threshold -35

# Check audio format support
python3 -m src.cli.main --list-formats
```

### If no files work:
```bash
# Test with a known good WAV file
# Or convert your audio:
ffmpeg -i input.mp3 output.wav
```

## 📋 **Test Checklist:**

- [ ] CLI loads without errors
- [ ] `--help` shows all expected options
- [ ] Can process a simple WAV file
- [ ] Whisper model loads successfully
- [ ] Can export to JSON format
- [ ] Church service profile loads
- [ ] Real speech produces transcription
- [ ] Processing completes without crashing

## 🎯 **Bottom Line:**

The **infrastructure is solid** and should work with real audio. The main limitation is that the speech detection algorithms need real audio data to properly distinguish speech from music.

**Test with actual human speech recordings** to validate the complete functionality.