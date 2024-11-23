import os
from abc import ABC, abstractmethod

class SpeechToTextInterface(ABC):

    def __init__(self):
        self.stt_endpoint = os.getenv('STT_ENDPOINT')

    @abstractmethod
    def transcribe(self, audio_buffer):
        pass

    def config_str(self):
        return f'endpoint: {self.stt_endpoint}'