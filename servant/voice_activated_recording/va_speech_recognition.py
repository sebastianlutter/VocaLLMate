import speech_recognition as sr
import numpy as np
import time
from servant.voice_activated_recording.va_interface import VoiceActivationInterface

class SpeechRecognitionActivated(VoiceActivationInterface):

    def __init__(self):
        super().__init__()
        self.wake_word = self.wakeword
        self.recognizer = sr.Recognizer()
        self.silence_threshold = self.wakeword_threshold

    def listen_for_wake_word(self):
        with sr.Microphone(device_index=self.soundcard.audio_microphone_device) as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("Listening for wake word...")
            transcript = ''
            while True:
                audio = self.recognizer.listen(source)
                try:
                    transcript = self.recognizer.recognize_vosk(audio, 'de').lower()
                    print(f"SpeechRecognition: Got {transcript}")
                    if self.wake_word in transcript:
                        print(f"Wake word '{self.wake_word}' detected. Starting recording...")
                        return self.start_recording()
                except sr.UnknownValueError as e:
                    print(f"Could not understand audio: {transcript}")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")

