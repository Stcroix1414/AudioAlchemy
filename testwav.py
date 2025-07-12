import wave
import sys
import os
import speech_recognition as sr

def check_wave_format(filepath):
    try:
        with wave.open(filepath, 'rb') as wf:
            print("✅ WAV file opened successfully.")
            print("Channels:", wf.getnchannels())
            print("Sample width (bytes):", wf.getsampwidth())
            print("Frame rate (Hz):", wf.getframerate())
            print("Number of frames:", wf.getnframes())
            print("Duration (seconds):", wf.getnframes() / wf.getframerate())
    except wave.Error as e:
        print("❌ wave.Error:", e)
        return False
    return True

def test_speech_recognition(filepath):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(filepath) as source:
            print("Reading audio...")
            audio_data = recognizer.record(source)
        print("Transcribing...")
        text = recognizer.recognize_google(audio_data)
        print("✅ Transcription result:", text)
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except sr.RequestError as e:
        print("❌ Request error:", e)
    except Exception as e:
        print("❌ General error:", e)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_wav_file.py path_to_audio.wav")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print("File does not exist:", path)
        sys.exit(1)

    print(f"\nTesting file: {path}")
    if check_wave_format(path):
        test_speech_recognition(path)
