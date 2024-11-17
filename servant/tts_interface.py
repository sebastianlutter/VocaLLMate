from abc import ABC, abstractmethod

class TextToSpeechInterface(ABC):

    @abstractmethod
    def speak(self, text: str):
        pass