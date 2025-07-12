# AudioAlchemy Local TTS Implementation Guide

This guide explains how to set up and use the local Text-to-Speech (TTS) voice cloning capabilities in AudioAlchemy.

## Overview

AudioAlchemy now supports local voice cloning using multiple TTS backends:

- **XTTS v2** (Coqui TTS) - Advanced multilingual voice cloning
- **Coqui TTS** - Open-source TTS with voice cloning
- **Tortoise-TTS** - High-quality voice synthesis

These local models provide:
- ✅ **Privacy**: Voice data stays on your machine
- ✅ **No API costs**: No per-use charges
- ✅ **Offline capability**: Works without internet
- ✅ **Customization**: Full control over voice models

## Quick Setup

### 1. Automated Setup (Recommended)

Run the setup script to automatically install dependencies:

```bash
python setup_local_tts.py
```

This script will:
- Check system requirements
- Install PyTorch and TTS libraries
- Download pre-trained models
- Test the installation

### 2. Manual Setup

If you prefer manual installation:

```bash
# Install PyTorch (CPU version)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install TTS backends
pip install TTS>=0.22.0
pip install tortoise-tts @ git+https://github.com/neonbjb/tortoise-tts.git

# Install audio processing libraries
pip install soundfile librosa scipy transformers accelerate
```

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB (8GB recommended)
- **Storage**: 2GB free space for models
- **FFmpeg**: For audio processing

### Recommended Requirements
- **Python**: 3.9+
- **RAM**: 8GB or more
- **GPU**: CUDA-compatible GPU (optional, improves speed)
- **Storage**: 5GB+ for multiple models

### System Dependencies

**Windows:**
- Download FFmpeg from https://ffmpeg.org/download.html
- Add FFmpeg to your system PATH

**macOS:**
```bash
brew install ffmpeg git
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg git
```

## Usage

### 1. Enable Voice Cloning

1. Start AudioAlchemy: `python app.py`
2. Navigate to **Voice Cloning** section
3. Read and accept the ethical guidelines
4. Click **"Enable Voice Cloning"**

### 2. Create a Voice Clone

1. Go to **"Create New Voice Clone"**
2. Enter a descriptive name for your voice
3. Upload an audio sample (10 seconds - 5 minutes)
4. Click **"Create Voice Clone"**

**Audio Requirements:**
- **Format**: WAV, MP3, M4A, FLAC, or OGG
- **Duration**: 10 seconds minimum, 5 minutes maximum
- **Quality**: 16kHz+ sample rate recommended
- **Content**: Clear speech, minimal background noise

### 3. Use Your Voice Clone

1. Go to the main **Voice Synthesis** tab
2. Enter text to convert to speech
3. Select your custom voice from the dropdown
4. Click **"Generate Speech"**

## Backend Comparison

| Backend | Quality | Speed | Languages | Memory Usage |
|---------|---------|-------|-----------|--------------|
| **XTTS v2** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 17+ | High |
| **Coqui TTS** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 10+ | Medium |
| **Tortoise-TTS** | ⭐⭐⭐⭐⭐ | ⭐⭐ | English | High |

### XTTS v2 (Recommended)
- **Best for**: High-quality multilingual voice cloning
- **Languages**: English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Hungarian, Korean, Hindi
- **Pros**: Excellent quality, multilingual, fast inference
- **Cons**: Large model size (~1.8GB)

### Coqui TTS
- **Best for**: Balanced quality and speed
- **Languages**: Multiple languages supported
- **Pros**: Good quality, reasonable speed, smaller models
- **Cons**: Limited compared to XTTS

### Tortoise-TTS
- **Best for**: Highest quality English speech
- **Languages**: English only
- **Pros**: Exceptional quality, very natural sounding
- **Cons**: Slow generation, English only, large memory usage

## Configuration

### Voice Cloning Provider Settings

In **Preferences**, you can set:

- **Voice Cloning Provider**: 
  - `auto` - Try ElevenLabs first, fallback to local
  - `elevenlabs` - ElevenLabs only
  - `local` - Local models only

- **Voice Cloning Quota**: Number of voice clones allowed (default: 5)

### Backend Selection

The system automatically selects the best available backend:

1. **XTTS v2** (if available)
2. **Coqui TTS** (if available)
3. **Tortoise-TTS** (if available)

## File Structure

```
AudioAlchemy/
├── local_tts_models.py          # Local TTS implementation
├── setup_local_tts.py           # Setup script
├── voice_models/                # Voice model storage
│   ├── xtts_[id]/              # XTTS voice models
│   ├── coqui_[id]/             # Coqui voice models
│   └── tortoise_[id]/          # Tortoise voice models
├── tts_cache/                   # Model cache
└── uploads/voice_models/        # Uploaded voice samples
```

## Troubleshooting

### Common Issues

**1. "No local TTS backends available"**
- Run `python setup_local_tts.py` to install dependencies
- Check that PyTorch is installed: `python -c "import torch; print(torch.__version__)"`

**2. "Audio validation failed"**
- Ensure audio is at least 10 seconds long
- Check audio quality (16kHz+ recommended)
- Try converting to WAV format first

**3. "Out of memory" errors**
- Close other applications to free RAM
- Try using CPU-only mode
- Use shorter audio samples

**4. Slow voice generation**
- First-time model loading is slow (models are downloaded)
- Consider using GPU acceleration if available
- XTTS is faster than Tortoise for generation

### Performance Tips

**Speed up voice cloning:**
- Use XTTS v2 backend (fastest)
- Keep audio samples under 60 seconds
- Use GPU if available

**Improve quality:**
- Use high-quality audio samples (22kHz+)
- Ensure clear speech with minimal background noise
- Use longer samples (30+ seconds) for better results

**Save storage:**
- Delete unused voice clones regularly
- Clear TTS cache periodically: `rm -rf tts_cache/*`

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export PYTHONPATH=.
export TTS_DEBUG=1
python app.py
```

## Advanced Configuration

### Custom Model Paths

You can specify custom model directories by modifying `local_tts_models.py`:

```python
# Custom paths
cloner = LocalVoiceCloner(
    models_dir="custom/voice/models",
    cache_dir="custom/tts/cache"
)
```

### GPU Acceleration

For CUDA-enabled systems, install GPU version of PyTorch:

```bash
# Replace CPU version with GPU version
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Memory Optimization

For systems with limited RAM, add to your environment:

```bash
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export OMP_NUM_THREADS=1
```

## API Reference

### LocalVoiceCloner Class

```python
from local_tts_models import local_voice_cloner

# Create voice clone
voice_id, message = local_voice_cloner.create_voice_clone(
    name="My Voice",
    description="Personal voice clone",
    audio_path="path/to/audio.wav",
    preferred_backend="xtts"  # or "auto", "coqui", "tortoise"
)

# Synthesize speech
success, message = local_voice_cloner.synthesize_speech(
    text="Hello, this is my cloned voice!",
    voice_id=voice_id,
    output_path="output.wav"
)

# List available voices
voices = local_voice_cloner.list_voice_clones()

# Delete voice clone
success, message = local_voice_cloner.delete_voice_clone(voice_id)
```

## Ethical Guidelines

**Important**: Local voice cloning must be used responsibly:

✅ **DO:**
- Only clone voices with explicit consent
- Clearly disclose when using synthetic voices
- Respect privacy and intellectual property
- Use for legitimate purposes only

❌ **DON'T:**
- Clone voices without permission
- Use for deception or fraud
- Create harmful or offensive content
- Violate laws or regulations

## Support

### Getting Help

1. **Check this guide** for common solutions
2. **Run diagnostics**: `python setup_local_tts.py`
3. **Check logs** in the application console
4. **Review system requirements** and dependencies

### Reporting Issues

When reporting issues, include:
- Operating system and version
- Python version
- Error messages (full traceback)
- Audio file details (format, duration, size)
- Available system memory

### Performance Benchmarks

Typical performance on different systems:

| System | Backend | Voice Creation | Speech Generation |
|--------|---------|----------------|-------------------|
| CPU (4 cores, 8GB RAM) | XTTS | 2-5 minutes | 5-10 seconds |
| CPU (8 cores, 16GB RAM) | XTTS | 1-3 minutes | 3-7 seconds |
| GPU (RTX 3060, 16GB RAM) | XTTS | 30-60 seconds | 1-3 seconds |

## Updates and Maintenance

### Updating Models

To update to newer model versions:

```bash
# Clear cache to force re-download
rm -rf tts_cache/*

# Update TTS library
pip install --upgrade TTS
```

### Backup Voice Models

Important voice models can be backed up:

```bash
# Backup voice models directory
tar -czf voice_models_backup.tar.gz voice_models/

# Restore from backup
tar -xzf voice_models_backup.tar.gz
```

## Conclusion

Local TTS voice cloning in AudioAlchemy provides powerful, private voice synthesis capabilities. With proper setup and responsible use, you can create high-quality custom voices for various applications while maintaining full control over your data.

For the best experience:
1. Use the automated setup script
2. Ensure adequate system resources
3. Use high-quality audio samples
4. Follow ethical guidelines
5. Keep models updated

Happy voice cloning! 🎭✨
