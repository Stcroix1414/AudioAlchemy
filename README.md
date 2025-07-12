# AudioAlchemy - The Art of Voice Transformation

A sophisticated Flask-based web application that provides professional-grade speech-to-text transcription, text translation, and text-to-speech synthesis with multiple AI provider support. AudioAlchemy combines cutting-edge AI technology with an elegant.

## Features

### 🎤 Speech Recognition
- Upload audio files in multiple formats (WAV, MP3, M4A, FLAC, OGG)
- Real-time speech-to-text transcription using Google Speech Recognition
- Automatic audio format conversion with FFmpeg
- Support for PCM WAV format optimization

### 🌍 Translation
- Multi-language translation powered by Google Translate
- Automatic language detection
- Support for 100+ languages
- Recent language tracking for quick access

### 🔊 Text-to-Speech (TTS)
- **Multiple TTS Providers:**
  - OpenAI TTS API (primary)
  - ElevenLabs (high-quality voices)
  - Google Text-to-Speech (fallback)
- Voice customization options
- Speed and quality controls
- Voice stability and clarity settings

### 🎭 Voice Cloning (NEW)
- **Ethical Voice Cloning:**
  - Create custom voice models from audio samples
  - ElevenLabs API integration for high-quality cloning
  - Consent-based system with ethical guidelines
  - Voice sample validation and quality checks
- **Voice Management:**
  - Upload audio files or record directly in browser
  - Voice library with preview and management tools
  - Quota system to prevent abuse
  - Secure voice data handling and retention policies
- **Advanced Features:**
  - Real-time voice preview with custom text
  - Voice quality validation (minimum 10 seconds, 16kHz)
  - Automatic audio format conversion
  - Voice clone deletion and cleanup

### 👤 User Management
- Personalized user preferences
- Customizable voice settings
- Theme selection (dark/light)
- Favorite phrases management
- Recent language history

### 📊 History & Analytics
- Complete transcription history
- Translation logs
- TTS generation tracking
- Downloadable results
- Session management

### 🎨 Professional Interface
- Sophisticated design
- Refined color palette with muted steel blue accents
- Professional typography using Inter/Source Sans Pro fonts
- Clean, minimal visual effects for mature presentation
- Responsive design optimized for business use
- Consistent AudioAlchemy branding across all pages

## Installation

### Prerequisites
- Python 3.8+
- FFmpeg (for audio conversion)
- Virtual environment (recommended)

### Quick Start

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Speech2txt
```

2. **Create and activate virtual environment:**
```bash
python -m venv myvenv
# Windows
myvenv\Scripts\activate
# Linux/Mac
source myvenv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install FFmpeg:**
   - **Windows:** Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - **Ubuntu/Debian:** `sudo apt install ffmpeg`
   - **macOS:** `brew install ffmpeg`

5. **Configure environment variables (optional):**
```bash
# Create .env file for API keys
echo "ELEVENLABS_API_KEY=your_elevenlabs_api_key_here" > .env
echo "OPENAI_API_KEY=your_openai_api_key_here" >> .env
```

6. **Run the application:**
```bash
python app.py
```

The application will be available at `http://localhost:80`

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# ElevenLabs API (optional)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# OpenAI API (optional)
OPENAI_API_KEY=your_openai_api_key_here

# Custom TTS Service (optional)
TTS_API_URL=http://your-tts-service:5050/v1/audio/speech
TTS_API_KEY=your_api_key_here
```

### TTS Provider Configuration

The application supports multiple TTS providers with automatic fallback:

1. **OpenAI TTS** (Primary)
   - High-quality voices (alloy, echo, fable, onyx, nova, shimmer)
   - Multiple models (tts-1, tts-1-hd)
   - Speed control (0.25x to 4.0x)

2. **ElevenLabs** (Premium)
   - Ultra-realistic voices
   - Voice cloning capabilities
   - Advanced voice settings (stability, clarity)

3. **Google TTS** (Fallback)
   - Free and reliable
   - Basic voice options
   - No API key required

## Usage

### Speech-to-Text
1. Upload an audio file using the file picker
2. Select target language for translation (optional)
3. Click "Process" to transcribe
4. Download transcription as text file

### Text-to-Speech
1. Enter text in the input field
2. Select voice and model preferences
3. Adjust voice settings if needed
4. Click "Generate Speech"
5. Download generated audio file

### User Preferences
- Access via the "Preferences" menu
- Customize default voice settings
- Set preferred TTS provider
- Configure theme and language preferences
- Manage favorite phrases

### History
- View all past transcriptions and translations
- Access previous TTS generations
- Export history data
- Search through past activities

## API Endpoints

### Core Functionality
- `POST /` - Main processing endpoint
- `GET /uploads/<filename>` - Serve uploaded files
- `GET /download_transcription` - Download transcription
- `GET /download_speech` - Download generated speech

### User Management
- `GET/POST /preferences` - User preferences
- `GET /history` - User history
- `GET /api/user-data` - Get user data (JSON)

### Favorites Management
- `POST /api/favorites` - Add favorite phrase
- `DELETE /api/favorites/<index>` - Remove favorite phrase

### Voice Management
- `GET /api/elevenlabs-voices` - Get available ElevenLabs voices

## Docker Deployment

The project includes Docker Compose configuration for additional AI services:

```bash
# Start additional AI services
docker-compose up -d

# The main Flask app runs separately
python app.py
```

### Services Included:
- **Ollama**: Local LLM server (port 11434)
- **OpenUI**: Web interface for AI models (port 7878)

## Project Structure

```
AudioAlchemy/
├── app.py                    # Main Flask application
├── launcher.py              # Application launcher
├── requirements.txt         # Python dependencies
├── docker-compose.yml       # Docker services configuration
├── .gitignore              # Git ignore rules
├── .env                    # Environment variables (create this)
├── app.spec                # PyInstaller spec for app
├── MyVoiceApp.spec         # PyInstaller spec for voice app
├── static/                 # Static web assets
│   ├── ChatGPT.png
│   └── style.css           # Professional styling with refined color palette
├── templates/              # HTML templates with AudioAlchemy branding
│   ├── enhanced_index.html # Main interface with professional design
│   ├── history.html        # Activity history with consistent navigation
│   ├── index.html          # Legacy template
│   ├── preferences.html    # User preferences with AudioAlchemy branding
│   ├── speech_to_text.html # Speech-to-text interface
│   ├── text_to_speech.html # Text-to-speech interface
│   └── voice_cloning.html  # Voice cloning studio with professional styling
├── uploads/                # User uploaded files (ignored)
├── backup/                 # Backup files (ignored)
├── build/                  # Build artifacts (ignored)
└── myvenv/                 # Virtual environment (ignored)
```

### Design Philosophy

AudioAlchemy features a professionally refined interface that eliminates childish visual elements while maintaining functionality:

- **Color Palette**: Sophisticated muted steel blue (#5a67d8) with professional gray accents
- **Typography**: Clean Inter/Source Sans Pro fonts for enhanced readability
- **Visual Effects**: Minimal, enterprise-appropriate styling without excessive animations
- **Branding**: Consistent AudioAlchemy identity with flask iconography across all pages
- **Navigation**: Unified navigation structure with proper active states

## Building Executable

The project includes PyInstaller specifications for creating standalone executables:

```bash
# Build the main application
pyinstaller app.spec

# Build the voice application
pyinstaller MyVoiceApp.spec
```

## Dependencies

### Core Dependencies
- **Flask**: Web framework
- **SpeechRecognition**: Speech-to-text processing
- **deep-translator**: Multi-language translation
- **elevenlabs**: Premium TTS service
- **openai-whisper**: Advanced speech recognition
- **pydub**: Audio processing
- **numpy**: Numerical computing
- **torch**: Machine learning framework

### System Dependencies
- **FFmpeg**: Audio format conversion
- **Git**: Version control (for Whisper installation)

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Install FFmpeg and ensure it's in your system PATH
   - Windows: Download from official site and add to PATH
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

2. **Audio conversion fails**
   - Check audio file format and size
   - Ensure FFmpeg is properly installed
   - Try converting audio manually first

3. **TTS not working**
   - Check API keys in .env file
   - Verify internet connection
   - Check TTS service availability

4. **Port 80 already in use**
   - Change port in app.py: `app.run(host='0.0.0.0', port=8080)`
   - Or stop other services using port 80

### Performance Tips

- Use smaller audio files for faster processing
- Enable hardware acceleration if available
- Use local TTS services for better performance
- Clear uploads folder periodically

## Security Features

- CSRF protection (Flask-WTF)
- Secure file uploads with validation
- Session management
- Input sanitization
- Environment variable protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing issues on GitHub
3. Create a new issue with detailed information

## Support AudioAlchemy Development

If you find AudioAlchemy helpful for your voice transformation needs, consider supporting its continued development and maintenance. Your contributions help keep this tool free and accessible to everyone.

### 💖 Donation Methods

#### Platform Donations
- **Buy Me a Coffee**: [coff.ee/stcroix14](https://coff.ee/stcroix14)
  - Quick and easy one-time or recurring support
  - Perfect for showing appreciation for the project

#### Cryptocurrency Donations
- **Solana (SOL)**: `BzYvTkZ2huyicfLRQP1d35NtLx1RtYZprfpTaRUiNELP`
  - Fast and low-cost transactions
  - QR codes available in the application interface
  - Copy address directly from the web interface

### 🎯 How Donations Help

Your support enables:
- **Continuous Development**: New features and improvements
- **Maintenance**: Bug fixes and security updates

### 🔒 Donation Security

- All donations are voluntary and non-refundable
- Cryptocurrency addresses are verified and secure
- No personal information is collected through donations
- Donations support open-source development

### 📊 Transparency

AudioAlchemy is committed to transparent development:
- Regular updates on project progress
- Open-source codebase for community review
- Clear roadmap for future features
- Community-driven development priorities

Thank you for supporting AudioAlchemy! 🙏

## 🗺️ Development Roadmap

*Realistic timeline for a solo developer working part-time*

### Current Version (v1.0) - ✅ Complete
- Core speech-to-text functionality
- Multi-language translation
- Text-to-speech with multiple providers
- Basic voice cloning capabilities
- User preferences and history
- Professional web interface

### Version 1.1 (Next 3-6 months)
- 🔧 **Bug Fixes & Stability**
  - Fix any reported issues
  - Improve error handling
  - Better file upload validation
- 🔧 **Small Quality of Life Improvements**
  - Remember user settings between sessions
  - Better mobile responsiveness
  - Improved audio player controls

### Version 1.2 (6-12 months)
- 📱 **Mobile Optimization**
  - Touch-friendly interface
  - Better mobile audio handling
- 🔊 **Audio Enhancements**
  - Support for more audio formats
  - Basic audio preprocessing (noise reduction)
  - Volume normalization

### Version 1.3 (1-2 years)
- 🤖 **AI Provider Expansion**
  - Add support for more TTS providers
  - Implement local Whisper for transcription
- 💾 **Data Management**
  - Export/import user data
  - Better file organization
  - Optional cloud storage integration

### Future Considerations (2+ years)
- 🌐 **API Development** (if there's demand)
- 📊 **Analytics Dashboard** (usage tracking)
- 🔌 **Plugin System** (for community extensions)

### Maintenance Goals
- 🛠️ **Regular Updates**: Security patches and dependency updates
- 📚 **Documentation**: Keep README and help docs current
- 🐛 **Issue Resolution**: Address user-reported bugs as time permits
- 🔄 **Backup Strategy**: Ensure project continuity

*Note: Timeline is flexible and depends on available development time and user feedback priorities.*

## Acknowledgments

- OpenAI for Whisper and TTS APIs
- ElevenLabs for premium voice synthesis
- Google for Speech Recognition and Translation services
- Flask community for the excellent web framework
- Our generous supporters and contributors
