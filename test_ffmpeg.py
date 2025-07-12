#!/usr/bin/env python3
import subprocess
import shutil
import os

print("Testing FFmpeg detection...")
print(f"Current PATH: {os.environ.get('PATH', 'Not found')[:200]}...")

# Method 1: Using shutil.which
ffmpeg_path = shutil.which('ffmpeg')
print(f"shutil.which('ffmpeg'): {ffmpeg_path}")

# Method 2: Direct subprocess call
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
    print(f"subprocess.run(['ffmpeg', '-version']): Success (return code: {result.returncode})")
except Exception as e:
    print(f"subprocess.run(['ffmpeg', '-version']): Failed - {e}")

# Method 3: Using shell=True
try:
    result = subprocess.run('ffmpeg -version', shell=True, capture_output=True, text=True, timeout=10)
    print(f"subprocess.run('ffmpeg -version', shell=True): Success (return code: {result.returncode})")
except Exception as e:
    print(f"subprocess.run('ffmpeg -version', shell=True): Failed - {e}")

# Method 4: Check specific path
chocolatey_path = r'C:\ProgramData\chocolatey\bin\ffmpeg.exe'
if os.path.exists(chocolatey_path):
    print(f"FFmpeg exists at: {chocolatey_path}")
    try:
        result = subprocess.run([chocolatey_path, '-version'], capture_output=True, text=True, timeout=10)
        print(f"Direct path call: Success (return code: {result.returncode})")
    except Exception as e:
        print(f"Direct path call: Failed - {e}")
else:
    print(f"FFmpeg not found at: {chocolatey_path}")
