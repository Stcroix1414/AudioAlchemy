import os
import uuid
import threading
import json
from datetime import datetime
from flask import Flask, request, render_template, redirect, send_file, flash, url_for, session, jsonify
from werkzeug.utils import secure_filename
import speech_recognition as sr
from deep_translator import GoogleTranslator
import requests
import subprocess
try:
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect()
except ImportError:
    csrf = None
try:
    from elevenlabs import generate, voices, set_api_key
except ImportError:
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import Voice, VoiceSettings
        ELEVENLABS_CLIENT = None
    except ImportError:
        print("ElevenLabs library not properly installed")
        ELEVENLABS_CLIENT = None

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'ogg'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize CSRF protection if available
if csrf:
    csrf.init_app(app)

# TTS configuration
TTS_API_URL = 'http://10.10.1.11:5050/v1/audio/speech'
TTS_API_KEY = 'your_api_key_here'
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', 'your_elevenlabs_api_key_here')

# Set ElevenLabs API key if available
try:
    if ELEVENLABS_API_KEY != 'your_elevenlabs_api_key_here':
        set_api_key(ELEVENLABS_API_KEY)
except NameError:
    # Handle newer ElevenLabs client
    if ELEVENLABS_API_KEY != 'your_elevenlabs_api_key_here':
        ELEVENLABS_CLIENT = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    else:
        ELEVENLABS_CLIENT = None

# User data storage
USER_DATA_FILE = 'user_data.json'
HISTORY_FILE = 'user_history.json'

# Latest outputs
latest_transcription = None
latest_translation = None
latest_audio_filename = None
latest_speech_filename = None

# User preferences structure
DEFAULT_USER_PREFS = {
    'name': 'User',
    'preferred_voice': 'alloy',
    'preferred_model': 'tts-1-hd',
    'preferred_language': 'en',
    'theme': 'dark',
    'voice_speed': 1.0,
    'voice_stability': 0.5,
    'voice_clarity': 0.75,
    'tts_provider': 'openai',  # 'openai', 'elevenlabs', 'gtts'
    'elevenlabs_voice_id': None,
    'favorite_phrases': [],
    'recent_languages': ['en', 'es', 'fr'],
    'voice_cloning_enabled': False,
    'voice_cloning_consent': False,
    'voice_cloning_provider': 'auto',  # 'auto', 'elevenlabs', 'local'
    'custom_voices': [],
    'voice_cloning_quota': 5,  # Number of voice clones allowed
    'voice_data_retention_days': 30
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_user_data():
    """Load user preferences from JSON file"""
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_USER_PREFS.copy()
    except Exception as e:
        print(f"Error loading user data: {e}")
        return DEFAULT_USER_PREFS.copy()

def save_user_data(user_data):
    """Save user preferences to JSON file"""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(user_data, f, indent=2)
    except Exception as e:
        print(f"Error saving user data: {e}")

def load_history():
    """Load user history from JSON file"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

def save_history(history):
    """Save user history to JSON file"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def add_to_history(action_type, content, metadata=None):
    """Add an entry to user history"""
    history = load_history()
    entry = {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'type': action_type,  # 'transcription', 'translation', 'tts'
        'content': content,
        'metadata': metadata or {}
    }
    history.insert(0, entry)  # Add to beginning
    # Keep only last 100 entries
    history = history[:100]
    save_history(history)

def get_elevenlabs_voices():
    """Get available ElevenLabs voices"""
    try:
        if ELEVENLABS_API_KEY != 'your_elevenlabs_api_key_here':
            try:
                # Try old API first
                voice_list = voices()
                return [(voice.voice_id, voice.name) for voice in voice_list]
            except NameError:
                # Try new API
                if ELEVENLABS_CLIENT:
                    voice_list = ELEVENLABS_CLIENT.voices.get_all()
                    return [(voice.voice_id, voice.name) for voice in voice_list.voices]
        return []
    except Exception as e:
        print(f"Error getting ElevenLabs voices: {e}")
        return []

def validate_voice_sample(filepath):
    """Validate voice sample for cloning"""
    try:
        # Check file size (minimum 10 seconds, maximum 5 minutes)
        file_size = os.path.getsize(filepath)
        if file_size < 100000:  # ~10 seconds of audio
            return False, "Audio sample too short. Minimum 10 seconds required."
        if file_size > 50000000:  # ~5 minutes of audio
            return False, "Audio sample too long. Maximum 5 minutes allowed."
        
        # Check audio quality using ffmpeg
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', filepath
            ], capture_output=True, text=True, check=True)
            
            import json
            audio_info = json.loads(result.stdout)
            
            # Check if it's audio
            audio_streams = [s for s in audio_info.get('streams', []) if s.get('codec_type') == 'audio']
            if not audio_streams:
                return False, "No audio stream found in file."
            
            # Check sample rate (minimum 16kHz recommended)
            sample_rate = int(audio_streams[0].get('sample_rate', 0))
            if sample_rate < 16000:
                return False, "Audio quality too low. Minimum 16kHz sample rate required."
            
            return True, "Voice sample validated successfully."
            
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return False, "Unable to validate audio format."
            
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def create_voice_clone_local(name, description, audio_file_path, user_id=None):
    """Create a voice clone using local TTS models (Tortoise-TTS or Coqui)"""
    try:
        from local_tts_models import local_voice_cloner
        
        # Check user quota
        user_data = load_user_data()
        if len(user_data.get('custom_voices', [])) >= user_data.get('voice_cloning_quota', 5):
            return None, "Voice cloning quota exceeded. Please remove existing voices or upgrade your plan."
        
        # Use the local voice cloner
        voice_id, message = local_voice_cloner.create_voice_clone(
            name=name,
            description=description,
            audio_path=audio_file_path,
            preferred_backend='auto'
        )
        
        if voice_id:
            # Get voice info from local cloner
            voice_info = local_voice_cloner.get_voice_info(voice_id)
            if voice_info:
                # Add user-specific metadata
                voice_info['user_id'] = user_id or 'default'
                voice_info['provider'] = 'local'
                
                # Add to user's custom voices
                user_data['custom_voices'].append(voice_info)
                save_user_data(user_data)
                
                # Add to history
                add_to_history('voice_clone', f"Created local voice clone: {name}", {
                    'voice_id': voice_id,
                    'name': name,
                    'description': description,
                    'provider': 'local',
                    'backend': voice_info.get('backend', 'unknown')
                })
        
        return voice_id, message
        
    except ImportError as e:
        return None, f"Local TTS models not available: {str(e)}"
    except Exception as e:
        return None, f"Local voice cloning error: {str(e)}"

def create_voice_clone(name, description, audio_file_path, user_id=None, provider='auto'):
    """Create a voice clone using specified provider or auto-select"""
    try:
        user_data = load_user_data()
        preferred_provider = user_data.get('voice_cloning_provider', 'auto')
        
        if provider == 'auto':
            provider = preferred_provider
        
        # Try ElevenLabs first if API key is available and provider allows
        if provider in ['auto', 'elevenlabs'] and ELEVENLABS_API_KEY != 'your_elevenlabs_api_key_here':
            try:
                # Validate the audio sample
                is_valid, message = validate_voice_sample(audio_file_path)
                if not is_valid:
                    return None, message
                
                # Check user quota
                if len(user_data.get('custom_voices', [])) >= user_data.get('voice_cloning_quota', 5):
                    return None, "Voice cloning quota exceeded. Please remove existing voices or upgrade your plan."
                
                # Create voice clone using ElevenLabs
                if ELEVENLABS_CLIENT:
                    # Use new API
                    with open(audio_file_path, 'rb') as audio_file:
                        voice = ELEVENLABS_CLIENT.clone(
                            name=name,
                            description=description,
                            files=[audio_file]
                        )
                    voice_id = voice.voice_id
                else:
                    # Use old API (if available)
                    from elevenlabs import clone
                    voice = clone(
                        name=name,
                        description=description,
                        files=[audio_file_path]
                    )
                    voice_id = voice.voice_id
                
                # Store voice information
                voice_info = {
                    'id': voice_id,
                    'name': name,
                    'description': description,
                    'created_at': datetime.now().isoformat(),
                    'file_path': audio_file_path,
                    'user_id': user_id or 'default',
                    'provider': 'elevenlabs'
                }
                
                # Add to user's custom voices
                user_data['custom_voices'].append(voice_info)
                save_user_data(user_data)
                
                # Add to history
                add_to_history('voice_clone', f"Created voice clone: {name}", {
                    'voice_id': voice_id,
                    'name': name,
                    'description': description,
                    'provider': 'elevenlabs'
                })
                
                return voice_id, "Voice clone created successfully using ElevenLabs."
                
            except Exception as e:
                if provider == 'elevenlabs':
                    return None, f"ElevenLabs API error: {str(e)}"
                # If auto mode, fall back to local
                print(f"ElevenLabs failed, falling back to local: {e}")
        
        # Use local voice cloning as fallback or if explicitly requested
        if provider in ['auto', 'local']:
            return create_voice_clone_local(name, description, audio_file_path, user_id)
        
        return None, f"Unsupported voice cloning provider: {provider}"
            
    except Exception as e:
        return None, f"Voice cloning error: {str(e)}"

def delete_voice_clone(voice_id):
    """Delete a voice clone"""
    try:
        user_data = load_user_data()
        
        # Find and remove voice from user data
        custom_voices = user_data.get('custom_voices', [])
        voice_to_remove = None
        
        for i, voice in enumerate(custom_voices):
            if voice['id'] == voice_id:
                voice_to_remove = custom_voices.pop(i)
                break
        
        if not voice_to_remove:
            return False, "Voice not found."
        
        provider = voice_to_remove.get('provider', 'elevenlabs')
        
        # Delete from appropriate provider
        if provider == 'elevenlabs':
            try:
                if ELEVENLABS_CLIENT:
                    ELEVENLABS_CLIENT.delete(voice_id)
                else:
                    from elevenlabs import delete
                    delete(voice_id)
            except Exception as e:
                print(f"Warning: Could not delete voice from ElevenLabs: {e}")
        
        elif provider == 'local':
            try:
                from local_tts_models import local_voice_cloner
                success, message = local_voice_cloner.delete_voice_clone(voice_id)
                if not success:
                    print(f"Warning: Could not delete local voice clone: {message}")
            except ImportError:
                print("Warning: Local TTS models not available for cleanup")
            except Exception as e:
                print(f"Warning: Could not delete local voice clone: {e}")
        
        # Clean up local file
        try:
            if 'file_path' in voice_to_remove and os.path.exists(voice_to_remove['file_path']):
                os.remove(voice_to_remove['file_path'])
        except Exception as e:
            print(f"Warning: Could not delete local file: {e}")
        
        # Save updated user data
        save_user_data(user_data)
        
        # Add to history
        add_to_history('voice_delete', f"Deleted voice clone: {voice_to_remove['name']}", {
            'voice_id': voice_id,
            'name': voice_to_remove['name'],
            'provider': provider
        })
        
        return True, "Voice clone deleted successfully."
        
    except Exception as e:
        return False, f"Error deleting voice clone: {str(e)}"

def get_user_custom_voices():
    """Get user's custom voice clones"""
    user_data = load_user_data()
    return user_data.get('custom_voices', [])

def text_to_speech_enhanced(text, voice, model, provider='openai', voice_settings=None):
    """Enhanced TTS function with multiple provider support"""
    filename = str(uuid.uuid4().hex) + ".mp3"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # Check if voice is a local voice clone
        if voice.startswith(('tortoise_', 'coqui_', 'xtts_', 'local_')):
            try:
                from local_tts_models import local_voice_cloner
                success, message = local_voice_cloner.synthesize_speech(text, voice, filepath)
                if success:
                    return filename
                else:
                    print(f"Local TTS failed: {message}")
                    # Fall through to other providers
            except ImportError:
                print("Local TTS models not available")
            except Exception as e:
                print(f"Local TTS error: {str(e)}")
        
        if provider == 'elevenlabs' and ELEVENLABS_API_KEY != 'your_elevenlabs_api_key_here':
            # Use ElevenLabs for high-quality TTS
            voice_settings = voice_settings or {}
            stability = voice_settings.get('stability', 0.5)
            similarity_boost = voice_settings.get('similarity_boost', 0.75)
            
            try:
                # Try old API first
                audio = generate(
                    text=text,
                    voice=voice,
                    model="eleven_multilingual_v2",
                    stream=False,
                    api_key=ELEVENLABS_API_KEY
                )
                
                with open(filepath, 'wb') as f:
                    f.write(audio)
                
                return filename
            except NameError:
                # Try new API
                if ELEVENLABS_CLIENT:
                    audio = ELEVENLABS_CLIENT.generate(
                        text=text,
                        voice=Voice(
                            voice_id=voice,
                            settings=VoiceSettings(
                                stability=stability,
                                similarity_boost=similarity_boost
                            )
                        ),
                        model="eleven_multilingual_v2"
                    )
                    
                    with open(filepath, 'wb') as f:
                        for chunk in audio:
                            f.write(chunk)
                    
                    return filename
                else:
                    raise Exception("ElevenLabs client not initialized")
            
        elif provider == 'openai':
            # Try OpenAI-compatible TTS service first
            try:
                requests.head(TTS_API_URL.split('/v1')[0], timeout=1)
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {TTS_API_KEY}"
                }
                payload = {
                    "model": model,
                    "input": text,
                    "voice": voice,
                    "speed": voice_settings.get('speed', 1.0) if voice_settings else 1.0
                }
                
                response = requests.post(TTS_API_URL, json=payload, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    return filename
                else:
                    print(f"OpenAI TTS API error: {response.status_code}")
                    raise Exception("OpenAI TTS failed")
                    
            except requests.exceptions.ConnectionError:
                print("OpenAI TTS service not available, falling back to gTTS")
                raise Exception("OpenAI TTS not available")
        
        # Fallback to gTTS
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filepath)
        return filename
        
    except Exception as e:
        print(f"Error in enhanced TTS ({provider}): {str(e)}")
        # Final fallback to gTTS
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(filepath)
            return filename
        except Exception as e2:
            print(f"Error in gTTS fallback: {str(e2)}")
            return None

def text_to_speech(text, voice, model):
    """Legacy function for backward compatibility"""
    user_prefs = load_user_data()
    provider = user_prefs.get('tts_provider', 'openai')
    
    voice_settings = {
        'speed': user_prefs.get('voice_speed', 1.0),
        'stability': user_prefs.get('voice_stability', 0.5),
        'similarity_boost': user_prefs.get('voice_clarity', 0.75)
    }
    
    # Use ElevenLabs voice if specified
    if provider == 'elevenlabs' and user_prefs.get('elevenlabs_voice_id'):
        voice = user_prefs['elevenlabs_voice_id']
    
    return text_to_speech_enhanced(text, voice, model, provider, voice_settings)

def convert_to_pcm_wav(filepath):
    try:
        output_path = filepath.rsplit('.', 1)[0] + "_converted.wav"
        command = ['ffmpeg', '-i', filepath, '-ac', '1', '-ar', '16000', '-sample_fmt', 's16', output_path]
        subprocess.run(command, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        raise ValueError(f"WAV conversion failed: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    global latest_transcription, latest_translation, latest_audio_filename, latest_speech_filename
    
    # Load user preferences
    user_prefs = load_user_data()

    if request.method == 'POST':
        file = request.files.get('file')
        target_language = request.form.get('target_language')
        text_input = request.form.get('text_input')
        selected_voice = request.form.get('voice', user_prefs['preferred_voice'])
        selected_model = request.form.get('model', user_prefs['preferred_model'])

        if text_input:
            latest_speech_filename = text_to_speech(text_input, selected_voice, selected_model)
            if latest_speech_filename:
                # Add to history
                add_to_history('tts', text_input, {
                    'voice': selected_voice,
                    'model': selected_model,
                    'provider': user_prefs.get('tts_provider', 'openai'),
                    'filename': latest_speech_filename
                })
            else:
                flash("Failed to generate speech. Please check the TTS service.", "flash-danger")

        if file and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                converted_path = convert_to_pcm_wav(filepath)
            except ValueError:
                flash("Invalid WAV file format. Please upload PCM WAV.", "flash-danger")
                return redirect(request.url)

            recognizer = sr.Recognizer()
            with sr.AudioFile(converted_path) as source:
                audio_data = recognizer.record(source)

            try:
                transcription = recognizer.recognize_google(audio_data)
                latest_transcription = transcription
                latest_audio_filename = os.path.basename(converted_path)
                
                # Add transcription to history
                add_to_history('transcription', transcription, {
                    'original_filename': file.filename,
                    'converted_filename': latest_audio_filename
                })

                if target_language:
                    latest_translation = GoogleTranslator(source='auto', target=target_language).translate(transcription)
                    
                    # Add translation to history
                    add_to_history('translation', latest_translation, {
                        'original_text': transcription,
                        'target_language': target_language,
                        'source_language': 'auto'
                    })
                    
                    # Update recent languages
                    if target_language not in user_prefs['recent_languages']:
                        user_prefs['recent_languages'].insert(0, target_language)
                        user_prefs['recent_languages'] = user_prefs['recent_languages'][:5]  # Keep only 5 recent
                        save_user_data(user_prefs)
                else:
                    latest_translation = None

            except sr.UnknownValueError:
                flash("Could not understand the audio.", "flash-danger")
            except sr.RequestError as e:
                flash(f"Speech recognition error: {e}", "flash-danger")

        elif not text_input:
            flash("No audio or text provided.", "flash-danger")

    # Get ElevenLabs voices for the UI
    elevenlabs_voices = get_elevenlabs_voices()

    return render_template('enhanced_index.html',
                           transcription=latest_transcription,
                           translated_text=latest_translation,
                           audio_file=latest_audio_filename,
                           speech_file=latest_speech_filename,
                           user_prefs=user_prefs,
                           elevenlabs_voices=elevenlabs_voices)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/download_transcription')
def download_transcription():
    if latest_transcription:
        filename = str(uuid.uuid4().hex) + ".txt"
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(path, 'w') as f:
            f.write(latest_transcription)
        return send_file(path, as_attachment=True)
    flash("No transcription to download.", "flash-danger")
    return redirect(url_for('index'))

@app.route('/download_speech')
def download_speech():
    if latest_speech_filename:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], latest_speech_filename), as_attachment=True)
    flash("No speech available to download.", "flash-danger")
    return redirect(url_for('index'))

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """User preferences page"""
    if request.method == 'POST':
        user_data = load_user_data()
        
        # Update preferences from form
        user_data['name'] = request.form.get('name', user_data['name'])
        user_data['preferred_voice'] = request.form.get('preferred_voice', user_data['preferred_voice'])
        user_data['preferred_model'] = request.form.get('preferred_model', user_data['preferred_model'])
        user_data['preferred_language'] = request.form.get('preferred_language', user_data['preferred_language'])
        user_data['theme'] = request.form.get('theme', user_data['theme'])
        user_data['tts_provider'] = request.form.get('tts_provider', user_data['tts_provider'])
        user_data['elevenlabs_voice_id'] = request.form.get('elevenlabs_voice_id', user_data['elevenlabs_voice_id'])
        
        # Voice cloning settings
        user_data['voice_cloning_provider'] = request.form.get('voice_cloning_provider', user_data.get('voice_cloning_provider', 'auto'))
        
        # Voice settings
        try:
            user_data['voice_speed'] = float(request.form.get('voice_speed', user_data['voice_speed']))
            user_data['voice_stability'] = float(request.form.get('voice_stability', user_data['voice_stability']))
            user_data['voice_clarity'] = float(request.form.get('voice_clarity', user_data['voice_clarity']))
            user_data['voice_cloning_quota'] = int(request.form.get('voice_cloning_quota', user_data.get('voice_cloning_quota', 5)))
            user_data['voice_data_retention_days'] = int(request.form.get('voice_data_retention_days', user_data.get('voice_data_retention_days', 30)))
        except ValueError:
            flash("Invalid voice settings values", "flash-danger")
            return redirect(request.url)
        
        save_user_data(user_data)
        flash("Preferences saved successfully!", "flash-success")
        return redirect(url_for('preferences'))
    
    user_data = load_user_data()
    elevenlabs_voices = get_elevenlabs_voices()
    
    return render_template('preferences.html', 
                         user_data=user_data, 
                         elevenlabs_voices=elevenlabs_voices)

@app.route('/history')
def history():
    """User history page"""
    user_history = load_history()
    return render_template('history.html', history=user_history)

@app.route('/api/favorites', methods=['POST'])
def add_favorite():
    """Add phrase to favorites"""
    data = request.get_json()
    phrase = data.get('phrase', '').strip()
    
    if not phrase:
        return jsonify({'error': 'No phrase provided'}), 400
    
    user_data = load_user_data()
    if phrase not in user_data['favorite_phrases']:
        user_data['favorite_phrases'].append(phrase)
        save_user_data(user_data)
    
    return jsonify({'success': True})

@app.route('/api/favorites/<int:index>', methods=['DELETE'])
def remove_favorite(index):
    """Remove phrase from favorites"""
    user_data = load_user_data()
    
    if 0 <= index < len(user_data['favorite_phrases']):
        user_data['favorite_phrases'].pop(index)
        save_user_data(user_data)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid index'}), 400

@app.route('/api/user-data')
def get_user_data():
    """Get user data for frontend"""
    return jsonify(load_user_data())

@app.route('/api/elevenlabs-voices')
def api_elevenlabs_voices():
    """Get ElevenLabs voices via API"""
    return jsonify(get_elevenlabs_voices())

@app.route('/voice-cloning', methods=['GET', 'POST'])
def voice_cloning():
    """Voice cloning management page"""
    user_data = load_user_data()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'enable_consent':
            # Handle voice cloning consent
            consent = request.form.get('voice_cloning_consent') == 'on'
            user_data['voice_cloning_consent'] = consent
            user_data['voice_cloning_enabled'] = consent
            save_user_data(user_data)
            
            if consent:
                flash("Voice cloning enabled. You can now create custom voices.", "flash-success")
            else:
                flash("Voice cloning disabled.", "flash-info")
            
            return redirect(url_for('voice_cloning'))
        
        elif action == 'create_voice' and user_data.get('voice_cloning_consent', False):
            # Handle voice clone creation
            voice_name = request.form.get('voice_name', '').strip()
            voice_description = request.form.get('voice_description', '').strip()
            audio_file = request.files.get('voice_sample')
            
            if not voice_name:
                flash("Voice name is required.", "flash-danger")
                return redirect(request.url)
            
            if not audio_file or not allowed_file(audio_file.filename):
                flash("Valid audio file is required.", "flash-danger")
                return redirect(request.url)
            
            # Save uploaded file
            filename = secure_filename(f"voice_sample_{uuid.uuid4().hex}_{audio_file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            audio_file.save(filepath)
            
            # Create voice clone
            voice_id, message = create_voice_clone(voice_name, voice_description, filepath)
            
            if voice_id:
                flash(message, "flash-success")
            else:
                flash(message, "flash-danger")
                # Clean up file if creation failed
                try:
                    os.remove(filepath)
                except:
                    pass
            
            return redirect(request.url)
    
    # Get user's custom voices
    custom_voices = get_user_custom_voices()
    
    return render_template('voice_cloning.html', 
                         user_data=user_data, 
                         custom_voices=custom_voices)

@app.route('/api/voice-clone', methods=['POST'])
def api_create_voice_clone():
    """API endpoint to create voice clone"""
    try:
        user_data = load_user_data()
        
        if not user_data.get('voice_cloning_consent', False):
            return jsonify({'error': 'Voice cloning consent required'}), 403
        
        data = request.get_json()
        voice_name = data.get('name', '').strip()
        voice_description = data.get('description', '').strip()
        audio_data = data.get('audio_data')  # Base64 encoded audio
        
        if not voice_name:
            return jsonify({'error': 'Voice name is required'}), 400
        
        if not audio_data:
            return jsonify({'error': 'Audio data is required'}), 400
        
        # Decode and save audio data
        import base64
        audio_bytes = base64.b64decode(audio_data)
        filename = f"voice_sample_{uuid.uuid4().hex}.wav"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
        
        # Create voice clone
        voice_id, message = create_voice_clone(voice_name, voice_description, filepath)
        
        if voice_id:
            return jsonify({
                'success': True,
                'voice_id': voice_id,
                'message': message
            })
        else:
            # Clean up file if creation failed
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/voice-clone/<voice_id>', methods=['DELETE'])
def api_delete_voice_clone(voice_id):
    """API endpoint to delete voice clone"""
    try:
        success, message = delete_voice_clone(voice_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/custom-voices')
def api_get_custom_voices():
    """Get user's custom voice clones"""
    try:
        custom_voices = get_user_custom_voices()
        return jsonify(custom_voices)
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/voice-clone/preview', methods=['POST'])
def api_preview_voice_clone():
    """Preview a custom voice with sample text"""
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        text = data.get('text', 'Hello! This is a preview of your custom voice.')
        
        if not voice_id:
            return jsonify({'error': 'Voice ID is required'}), 400
        
        # Generate speech using the custom voice
        filename = text_to_speech_enhanced(
            text=text,
            voice=voice_id,
            model='eleven_multilingual_v2',
            provider='elevenlabs'
        )
        
        if filename:
            return jsonify({
                'success': True,
                'audio_url': url_for('uploaded_file', filename=filename)
            })
        else:
            return jsonify({'error': 'Failed to generate preview'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def run_flask():
    app.run(host='0.0.0.0', port=80, debug=True)

if __name__ == '__main__':
    run_flask()
