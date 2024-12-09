import os
from abc import ABC, abstractmethod

class SpeechToTextInterface(ABC):

    def __init__(self):
        self.stt_endpoint = os.getenv('STT_ENDPOINT', 'http://127.0.0.1:8000/v1/audio/transcriptions')

    @abstractmethod
    def transcribe(self, audio_buffer):
        pass

    def config_str(self):
        return f'endpoint: {self.stt_endpoint}'