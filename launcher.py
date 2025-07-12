import webbrowser
import subprocess

subprocess.Popen(['app.exe'])  # Starts your frozen Flask app
webbrowser.open('http://127.0.0.1:5000')  # Opens it in the browser
