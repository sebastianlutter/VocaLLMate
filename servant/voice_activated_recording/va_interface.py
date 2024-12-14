import time
import os
import random
import numpy as np
from abc import ABC, abstractmethod
from servant.audio_device.soundcard_factory import SoundcardFactory
from servant.tts.tts_factory import TtsFactory


class VoiceActivationInterface(ABC):

    def __init__(self):
        super().__init__()
        self.wakeword = os.getenv('WAKEWORD', 'computer')
        self.wakeword_threshold = int(os.getenv('WAKEWORD_THRESHOLD', '250'))
        # Configurable delay before counting silence
        self.silence_lead_time = 2
        self.soundcard = SoundcardFactory()
        self.tts_provider = TtsFactory()

    @abstractmethod
    def listen_for_wake_word(self):
        pass

    def random_hi(self):
        activated_sentences = ['ja', 'schiess los!', 'was gibts?', 'hi', 'leg los', 'was willst du?']
        return random.choice(activated_sentences)

    def start_recording(self, test = False):
        self.tts_provider.speak(self.random_hi())
        print("Recording...")
        stream = self.soundcard.get_record_stream()
        audio_frames = []
        silence_counter = 0
        record_start_time = time.time()
        while True:
            data = stream.read(self.soundcard.frames_per_buffer, exception_on_overflow=False)
            if time.time() - record_start_time < self.silence_lead_time:
                audio_frames.append(data)
            else:
                if test:
                    break
                if self.is_silence(data):
                    silence_counter += 1
                else:
                    silence_counter = 0
                audio_frames.append(data)
            if silence_counter > 30:  # approx 2 seconds of silence detected
                break
        print("Stopping recording...")
        stream.stop_stream()
        stream.close()
        # Remove the last two seconds of audio corresponding to silence detection
        return self.soundcard.get_audio_buffer(audio_frames[:-30])


    def config_str(self):
        return f'wakeword: {self.wakeword}, threshold: {self.wakeword_threshold}'

    def is_silence(self, data):
        audio_data = np.frombuffer(data, dtype=np.int16)
        mean_volume = np.mean(np.abs(audio_data))
        return mean_volume < self.wakeword_threshold