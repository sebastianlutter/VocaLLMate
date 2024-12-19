import os
from abc import ABC, abstractmethod


class VoiceActivationInterface(ABC):

    def __init__(self):
        super().__init__()
        self.wakeword = os.getenv('WAKEWORD', 'computer')
        self.wakeword_threshold = int(os.getenv('WAKEWORD_THRESHOLD', '250'))
        # Configurable delay before counting silence
        self.silence_lead_time = 2


    @abstractmethod
    def listen_for_wake_word(self) -> None:
        """
        This function should block until the wakeword has been detected
        """
        pass

    def config_str(self):
        return f'wakeword: {self.wakeword}, threshold: {self.wakeword_threshold}'
