"""
Local TTS Models Implementation for AudioAlchemy
Provides local voice cloning capabilities using Tortoise-TTS and Coqui TTS
"""

import os
import json
import uuid
import torch
import torchaudio
import numpy as np
from datetime import datetime
from pathlib import Path
import subprocess
import logging
from typing import Optional, Tuple, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalVoiceCloner:
    """Local voice cloning implementation using multiple TTS backends"""
    
    def __init__(self, models_dir: str = "voice_models", cache_dir: str = "tts_cache"):
        self.models_dir = Path(models_dir)
        self.cache_dir = Path(cache_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize available backends
        self.backends = self._detect_available_backends()
        logger.info(f"Available TTS backends: {list(self.backends.keys())}")
        
    def _detect_available_backends(self) -> Dict[str, bool]:
        """Detect which TTS backends are available"""
        backends = {}
        
        # Check for Tortoise-TTS
        try:
            import tortoise
            backends['tortoise'] = True
            logger.info("Tortoise-TTS backend available")
        except ImportError:
            backends['tortoise'] = False
            logger.warning("Tortoise-TTS not available - install with: pip install tortoise-tts")
        
        # Check for Coqui TTS
        try:
            import TTS
            backends['coqui'] = True
            logger.info("Coqui TTS backend available")
        except ImportError:
            backends['coqui'] = False
            logger.warning("Coqui TTS not available - install with: pip install TTS")
        
        # Check for XTTS (part of Coqui)
        try:
            from TTS.api import TTS as CoquiTTS
            # Try to load XTTS model
            backends['xtts'] = True
            logger.info("XTTS backend available")
        except (ImportError, Exception):
            backends['xtts'] = False
            logger.warning("XTTS not available")
        
        return backends
    
    def validate_audio_sample(self, audio_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate audio sample for voice cloning"""
        try:
            # Load audio file
            waveform, sample_rate = torchaudio.load(audio_path)
            
            # Get audio info
            duration = waveform.shape[1] / sample_rate
            channels = waveform.shape[0]
            
            # Validation checks
            if duration < 10.0:
                return False, f"Audio too short: {duration:.1f}s (minimum 10s required)", {}
            
            if duration > 300.0:  # 5 minutes
                return False, f"Audio too long: {duration:.1f}s (maximum 300s allowed)", {}
            
            if sample_rate < 16000:
                return False, f"Sample rate too low: {sample_rate}Hz (minimum 16kHz required)", {}
            
            # Check for silence
            rms = torch.sqrt(torch.mean(waveform**2))
            if rms < 0.01:
                return False, "Audio appears to be mostly silent", {}
            
            # Audio quality metrics
            audio_info = {
                'duration': duration,
                'sample_rate': sample_rate,
                'channels': channels,
                'rms_level': float(rms),
                'file_size': os.path.getsize(audio_path)
            }
            
            return True, "Audio sample validated successfully", audio_info
            
        except Exception as e:
            return False, f"Audio validation error: {str(e)}", {}
    
    def preprocess_audio(self, input_path: str, output_path: str) -> bool:
        """Preprocess audio for voice cloning"""
        try:
            # Load audio
            waveform, sample_rate = torchaudio.load(input_path)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 22kHz (standard for most TTS models)
            if sample_rate != 22050:
                resampler = torchaudio.transforms.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
                sample_rate = 22050
            
            # Normalize audio
            waveform = waveform / torch.max(torch.abs(waveform))
            
            # Apply basic noise reduction (simple high-pass filter)
            highpass = torchaudio.transforms.HighpassBiquad(sample_rate, cutoff_freq=80)
            waveform = highpass(waveform)
            
            # Save preprocessed audio
            torchaudio.save(output_path, waveform, sample_rate)
            
            logger.info(f"Audio preprocessed: {input_path} -> {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {str(e)}")
            return False
    
    def create_voice_clone_tortoise(self, name: str, description: str, audio_path: str) -> Tuple[Optional[str], str]:
        """Create voice clone using Tortoise-TTS"""
        if not self.backends.get('tortoise', False):
            return None, "Tortoise-TTS backend not available"
        
        try:
            from tortoise.api import TextToSpeech
            from tortoise.utils.audio import load_voices
            
            voice_id = f"tortoise_{uuid.uuid4().hex[:12]}"
            voice_dir = self.models_dir / voice_id
            voice_dir.mkdir(exist_ok=True)
            
            # Preprocess audio
            processed_audio = voice_dir / "voice_sample.wav"
            if not self.preprocess_audio(audio_path, str(processed_audio)):
                return None, "Audio preprocessing failed"
            
            # Create voice directory structure for Tortoise
            voice_samples_dir = voice_dir / "samples"
            voice_samples_dir.mkdir(exist_ok=True)
            
            # Copy processed audio to samples directory
            import shutil
            shutil.copy(str(processed_audio), str(voice_samples_dir / "sample_0.wav"))
            
            # Create voice metadata
            voice_info = {
                'id': voice_id,
                'name': name,
                'description': description,
                'backend': 'tortoise',
                'created_at': datetime.now().isoformat(),
                'audio_path': str(processed_audio),
                'samples_dir': str(voice_samples_dir),
                'status': 'ready'
            }
            
            # Save voice metadata
            with open(voice_dir / "voice_info.json", 'w') as f:
                json.dump(voice_info, f, indent=2)
            
            logger.info(f"Tortoise voice clone created: {voice_id}")
            return voice_id, "Voice clone created successfully with Tortoise-TTS"
            
        except Exception as e:
            logger.error(f"Tortoise voice cloning failed: {str(e)}")
            return None, f"Tortoise voice cloning error: {str(e)}"
    
    def create_voice_clone_coqui(self, name: str, description: str, audio_path: str) -> Tuple[Optional[str], str]:
        """Create voice clone using Coqui TTS"""
        if not self.backends.get('coqui', False):
            return None, "Coqui TTS backend not available"
        
        try:
            from TTS.api import TTS as CoquiTTS
            
            voice_id = f"coqui_{uuid.uuid4().hex[:12]}"
            voice_dir = self.models_dir / voice_id
            voice_dir.mkdir(exist_ok=True)
            
            # Preprocess audio
            processed_audio = voice_dir / "voice_sample.wav"
            if not self.preprocess_audio(audio_path, str(processed_audio)):
                return None, "Audio preprocessing failed"
            
            # Initialize Coqui TTS with a voice cloning model
            tts = CoquiTTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False)
            
            # Create voice metadata
            voice_info = {
                'id': voice_id,
                'name': name,
                'description': description,
                'backend': 'coqui',
                'created_at': datetime.now().isoformat(),
                'audio_path': str(processed_audio),
                'model_path': str(voice_dir),
                'status': 'ready'
            }
            
            # Save voice metadata
            with open(voice_dir / "voice_info.json", 'w') as f:
                json.dump(voice_info, f, indent=2)
            
            logger.info(f"Coqui voice clone created: {voice_id}")
            return voice_id, "Voice clone created successfully with Coqui TTS"
            
        except Exception as e:
            logger.error(f"Coqui voice cloning failed: {str(e)}")
            return None, f"Coqui voice cloning error: {str(e)}"
    
    def create_voice_clone_xtts(self, name: str, description: str, audio_path: str) -> Tuple[Optional[str], str]:
        """Create voice clone using XTTS (Coqui's advanced model)"""
        if not self.backends.get('xtts', False):
            return None, "XTTS backend not available"
        
        try:
            from TTS.api import TTS as CoquiTTS
            
            voice_id = f"xtts_{uuid.uuid4().hex[:12]}"
            voice_dir = self.models_dir / voice_id
            voice_dir.mkdir(exist_ok=True)
            
            # Preprocess audio
            processed_audio = voice_dir / "voice_sample.wav"
            if not self.preprocess_audio(audio_path, str(processed_audio)):
                return None, "Audio preprocessing failed"
            
            # Initialize XTTS model
            tts = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
            
            # Create voice metadata
            voice_info = {
                'id': voice_id,
                'name': name,
                'description': description,
                'backend': 'xtts',
                'created_at': datetime.now().isoformat(),
                'audio_path': str(processed_audio),
                'model_path': str(voice_dir),
                'status': 'ready'
            }
            
            # Save voice metadata
            with open(voice_dir / "voice_info.json", 'w') as f:
                json.dump(voice_info, f, indent=2)
            
            logger.info(f"XTTS voice clone created: {voice_id}")
            return voice_id, "Voice clone created successfully with XTTS"
            
        except Exception as e:
            logger.error(f"XTTS voice cloning failed: {str(e)}")
            return None, f"XTTS voice cloning error: {str(e)}"
    
    def create_voice_clone(self, name: str, description: str, audio_path: str, 
                          preferred_backend: str = 'auto') -> Tuple[Optional[str], str]:
        """Create voice clone using the best available backend"""
        
        # Validate audio first
        is_valid, message, audio_info = self.validate_audio_sample(audio_path)
        if not is_valid:
            return None, message
        
        # Determine backend to use
        if preferred_backend == 'auto':
            # Priority order: XTTS > Coqui > Tortoise
            if self.backends.get('xtts', False):
                preferred_backend = 'xtts'
            elif self.backends.get('coqui', False):
                preferred_backend = 'coqui'
            elif self.backends.get('tortoise', False):
                preferred_backend = 'tortoise'
            else:
                return None, "No local TTS backends available"
        
        # Create voice clone with selected backend
        if preferred_backend == 'xtts':
            return self.create_voice_clone_xtts(name, description, audio_path)
        elif preferred_backend == 'coqui':
            return self.create_voice_clone_coqui(name, description, audio_path)
        elif preferred_backend == 'tortoise':
            return self.create_voice_clone_tortoise(name, description, audio_path)
        else:
            return None, f"Unsupported backend: {preferred_backend}"
    
    def synthesize_speech(self, text: str, voice_id: str, output_path: str) -> Tuple[bool, str]:
        """Synthesize speech using a cloned voice"""
        try:
            # Load voice metadata
            voice_dir = self.models_dir / voice_id
            voice_info_path = voice_dir / "voice_info.json"
            
            if not voice_info_path.exists():
                return False, f"Voice {voice_id} not found"
            
            with open(voice_info_path, 'r') as f:
                voice_info = json.load(f)
            
            backend = voice_info['backend']
            
            if backend == 'tortoise':
                return self._synthesize_tortoise(text, voice_info, output_path)
            elif backend == 'coqui':
                return self._synthesize_coqui(text, voice_info, output_path)
            elif backend == 'xtts':
                return self._synthesize_xtts(text, voice_info, output_path)
            else:
                return False, f"Unsupported backend: {backend}"
                
        except Exception as e:
            logger.error(f"Speech synthesis failed: {str(e)}")
            return False, f"Speech synthesis error: {str(e)}"
    
    def _synthesize_tortoise(self, text: str, voice_info: Dict, output_path: str) -> Tuple[bool, str]:
        """Synthesize speech using Tortoise-TTS"""
        try:
            from tortoise.api import TextToSpeech
            
            tts = TextToSpeech()
            
            # Load voice samples
            voice_samples = []
            samples_dir = Path(voice_info['samples_dir'])
            for sample_file in samples_dir.glob("*.wav"):
                voice_samples.append(str(sample_file))
            
            if not voice_samples:
                return False, "No voice samples found"
            
            # Generate speech
            gen = tts.tts_with_preset(text, voice_samples=voice_samples, preset='fast')
            
            # Save output
            torchaudio.save(output_path, gen.squeeze(0).cpu(), 24000)
            
            return True, "Speech synthesized successfully with Tortoise-TTS"
            
        except Exception as e:
            return False, f"Tortoise synthesis error: {str(e)}"
    
    def _synthesize_coqui(self, text: str, voice_info: Dict, output_path: str) -> Tuple[bool, str]:
        """Synthesize speech using Coqui TTS"""
        try:
            from TTS.api import TTS as CoquiTTS
            
            tts = CoquiTTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False)
            
            # Generate speech
            tts.tts_to_file(
                text=text,
                speaker_wav=voice_info['audio_path'],
                file_path=output_path
            )
            
            return True, "Speech synthesized successfully with Coqui TTS"
            
        except Exception as e:
            return False, f"Coqui synthesis error: {str(e)}"
    
    def _synthesize_xtts(self, text: str, voice_info: Dict, output_path: str) -> Tuple[bool, str]:
        """Synthesize speech using XTTS"""
        try:
            from TTS.api import TTS as CoquiTTS
            
            tts = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
            
            # Generate speech
            tts.tts_to_file(
                text=text,
                speaker_wav=voice_info['audio_path'],
                language="en",
                file_path=output_path
            )
            
            return True, "Speech synthesized successfully with XTTS"
            
        except Exception as e:
            return False, f"XTTS synthesis error: {str(e)}"
    
    def list_voice_clones(self) -> list:
        """List all available voice clones"""
        voices = []
        
        for voice_dir in self.models_dir.iterdir():
            if voice_dir.is_dir():
                voice_info_path = voice_dir / "voice_info.json"
                if voice_info_path.exists():
                    try:
                        with open(voice_info_path, 'r') as f:
                            voice_info = json.load(f)
                        voices.append(voice_info)
                    except Exception as e:
                        logger.warning(f"Failed to load voice info for {voice_dir.name}: {e}")
        
        return voices
    
    def delete_voice_clone(self, voice_id: str) -> Tuple[bool, str]:
        """Delete a voice clone"""
        try:
            voice_dir = self.models_dir / voice_id
            
            if not voice_dir.exists():
                return False, f"Voice {voice_id} not found"
            
            # Remove voice directory and all contents
            import shutil
            shutil.rmtree(voice_dir)
            
            logger.info(f"Voice clone deleted: {voice_id}")
            return True, "Voice clone deleted successfully"
            
        except Exception as e:
            logger.error(f"Failed to delete voice clone {voice_id}: {str(e)}")
            return False, f"Delete error: {str(e)}"
    
    def get_voice_info(self, voice_id: str) -> Optional[Dict]:
        """Get information about a voice clone"""
        try:
            voice_dir = self.models_dir / voice_id
            voice_info_path = voice_dir / "voice_info.json"
            
            if not voice_info_path.exists():
                return None
            
            with open(voice_info_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to get voice info for {voice_id}: {str(e)}")
            return None

# Global instance
local_voice_cloner = LocalVoiceCloner()
