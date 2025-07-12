#!/usr/bin/env python3
"""
Setup script for AudioAlchemy Local TTS Models
This script helps install and configure local TTS backends
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(command, description=""):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"Running: {description or command}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ Success: {description or command}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description or command}")
        print(f"Error code: {e.returncode}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required for local TTS models")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_system_dependencies():
    """Check for required system dependencies"""
    print("\n🔍 Checking system dependencies...")
    
    dependencies = {
        'ffmpeg': 'FFmpeg (audio processing)',
        'git': 'Git (for package installation)',
    }
    
    missing = []
    for cmd, desc in dependencies.items():
        # Use shutil.which() for better cross-platform compatibility
        if shutil.which(cmd):
            print(f"✅ {desc} is installed")
        else:
            print(f"❌ {desc} is missing")
            missing.append(cmd)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("\nPlease install them:")
        
        system = platform.system().lower()
        if system == 'windows':
            print("Windows:")
            print("- FFmpeg: Download from https://ffmpeg.org/download.html")
            print("- Git: Download from https://git-scm.com/download/win")
        elif system == 'darwin':  # macOS
            print("macOS (using Homebrew):")
            print("brew install ffmpeg git")
        else:  # Linux
            print("Ubuntu/Debian:")
            print("sudo apt update && sudo apt install ffmpeg git")
            print("\nCentOS/RHEL/Fedora:")
            print("sudo yum install ffmpeg git")
        
        return False
    
    return True

def install_pytorch():
    """Install PyTorch with appropriate configuration"""
    print("\n🔥 Installing PyTorch...")
    
    # Check if CUDA is available
    try:
        import torch
        if torch.cuda.is_available():
            print("✅ PyTorch with CUDA support already installed")
            print(f"CUDA version: {torch.version.cuda}")
            print(f"Available GPUs: {torch.cuda.device_count()}")
            return True
        else:
            print("ℹ️  PyTorch installed but no CUDA support detected")
    except ImportError:
        pass
    
    # Install PyTorch with CUDA support (CUDA 12.1 compatible)
    pytorch_cmd = "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121"
    return run_command(pytorch_cmd, "Installing PyTorch with CUDA 12.1 support")

def install_tts_backends():
    """Install TTS backend libraries"""
    print("\n🎤 Installing TTS backends...")
    
    # Install core dependencies first
    core_deps = [
        ("pip install soundfile librosa scipy accelerate", "Audio processing libraries"),
        ("pip install TTS>=0.22.0", "Coqui TTS (XTTS support)"),
    ]
    
    success_count = 0
    for cmd, desc in core_deps:
        if run_command(cmd, desc):
            success_count += 1
    
    # Try to install Tortoise-TTS separately (optional)
    print("\n🐢 Attempting to install Tortoise-TTS (optional)...")
    tortoise_success = run_command(
        "pip install tortoise-tts @ git+https://github.com/neonbjb/tortoise-tts.git", 
        "Tortoise-TTS (optional - may have dependency conflicts)"
    )
    
    if tortoise_success:
        success_count += 1
        print("✅ Tortoise-TTS installed successfully")
    else:
        print("⚠️  Tortoise-TTS installation failed due to dependency conflicts")
        print("   This is normal - XTTS and Coqui TTS will still work fine")
        print("   You can install Tortoise-TTS manually later if needed")
    
    print(f"\n📊 Installed {success_count}/{len(core_deps)} core TTS backends successfully")
    return success_count >= 1  # Only need core backends to work

def create_directories():
    """Create necessary directories for voice models"""
    print("\n📁 Creating directories...")
    
    directories = [
        "voice_models",
        "tts_cache",
        "uploads/voice_models",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def test_installation():
    """Test if the installation works"""
    print("\n🧪 Testing installation...")
    
    try:
        from local_tts_models import LocalVoiceCloner
        cloner = LocalVoiceCloner()
        
        available_backends = [name for name, available in cloner.backends.items() if available]
        
        if available_backends:
            print(f"✅ Local TTS installation successful!")
            print(f"Available backends: {', '.join(available_backends)}")
            return True
        else:
            print("⚠️  No TTS backends are available")
            print("This might be due to missing dependencies or installation issues")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Local TTS models may not be properly installed")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def download_models():
    """Download pre-trained models"""
    print("\n� Downloading pre-trained models...")
    
    try:
        # Download XTTS model (this will be cached for future use)
        print("Downloading XTTS v2 model (this may take a while)...")
        from TTS.api import TTS
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        print("✅ XTTS v2 model downloaded successfully")
        return True
    except Exception as e:
        print(f"⚠️  Model download failed: {e}")
        print("Models will be downloaded automatically when first used")
        return False

def main():
    """Main setup function"""
    print("🎭 AudioAlchemy Local TTS Setup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    if not check_system_dependencies():
        print("\n❌ Please install missing system dependencies and run this script again")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install Python packages
    print("\n📦 Installing Python packages...")
    
    # Install PyTorch first
    if not install_pytorch():
        print("❌ Failed to install PyTorch")
        sys.exit(1)
    
    # Install TTS backends
    if not install_tts_backends():
        print("❌ Failed to install TTS backends")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("❌ Installation test failed")
        sys.exit(1)
    
    # Download models (optional)
    download_models()
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the AudioAlchemy application: python app.py")
    print("2. Go to Voice Cloning section")
    print("3. Enable voice cloning consent")
    print("4. Create your first voice clone!")
    print("\nNote: First-time model loading may take a few minutes")

if __name__ == "__main__":
    main()
