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
    'recent_languages': ['en', 'es', 'fr']
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

def text_to_speech_enhanced(text, voice, model, provider='openai', voice_settings=None):
    """Enhanced TTS function with multiple provider support"""
    filename = str(uuid.uuid4().hex) + ".mp3"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
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
        
        # Voice settings
        try:
            user_data['voice_speed'] = float(request.form.get('voice_speed', user_data['voice_speed']))
            user_data['voice_stability'] = float(request.form.get('voice_stability', user_data['voice_stability']))
            user_data['voice_clarity'] = float(request.form.get('voice_clarity', user_data['voice_clarity']))
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

def run_flask():
    app.run(host='0.0.0.0', port=80, debug=True)

if __name__ == '__main__':
    run_flask()
