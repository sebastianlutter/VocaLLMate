import json
import requests
from servant.stt.stt_interface import SpeechToTextInterface
import speech_recognition as sr

class SpeechToTextSpeechRecognitionLocal(SpeechToTextInterface):

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()

    def transcribe(self, audio_buffer):
        # audio_buffer is a BytesIO object containing WAV data
        # Step 1: Use AudioFile to interpret the BytesIO stream as a wave file
        with sr.AudioFile(audio_buffer) as source:
            # Step 2: Convert the audio file into AudioData
            audio_data = self.recognizer.record(source)
        # audio_buffer is a BytesIO object containing WAV data
        # Step 3: Now that we have AudioData, we can use recognize_vosk
        transcript = self.recognizer.recognize_vosk(audio_data, language='de').lower()
        print("Transcript:", transcript)
        return transcript
