from abc import ABC, abstractmethod

class SpeechToTextInterface(ABC):

    @abstractmethod
    def transcribe(self, audio_buffer):
        pass