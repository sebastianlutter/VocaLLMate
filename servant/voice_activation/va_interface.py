import queue
import time
import os
from threading import Thread
from abc import ABC, abstractmethod

class VoiceActivationInterface(ABC):

    def __init__(self):
        super().__init__()
        self.wakeword = os.getenv('WAKEWORD')
        self.wakeword_threshold = os.getenv('WAKEWORD_THRESHOLD')
        self.audio_microphone_device = int(os.getenv('AUDIO_MICROPHONE_DEVICE'))
        if self.audio_microphone_device < 0:
            self.audio_microphone_device = None

    @abstractmethod
    def listen_for_wake_word(self, sentence: str):
        pass

    @abstractmethod
    def start_recording(self):
        pass

    def config_str(self):
        return f'wakeword: {self.wakeword}, threshold: {self.wakeword_threshold}'