import pvporcupine
import pyaudio
import os
import sys
import numpy as np
from servant.voice_activated_recording.va_interface import VoiceActivationInterface


class PorcupineWakeWord(VoiceActivationInterface):
    def __init__(self):
        super().__init__()
        self.model_path=f'./{self.wakeword}_de_linux_v3_0_0.ppn'
        if not os.path.isfile(self.model_path):
            print(f"Picovoice model file is missing. Cannot find {self.model_path}")
            print("Please make an account and download one: https://picovoice.ai/")
            sys.exit(0)
        self.porcupine = pvporcupine.create(
            keyword_paths=[self.model_path],
            model_path='./porcupine_params_de.pv',
            # sensitivity between 0.0 and 1.0
            sensitivities=[self.wakeword_threshold/500.0],
            access_key=os.getenv('PICOVOICE_ACCESS_KEY')
        )
        self.audio_interface = pyaudio.PyAudio()
        self.stream = None

    def listen_for_wake_word(self) -> None:
        try:
            print("Initializing audio stream...")
            self.stream = self.audio_interface.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            print(f"Listening for wake word: {self.wakeword}")
            while True:
                pcm = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = np.frombuffer(pcm, dtype=np.int16)
                result = self.porcupine.process(pcm)
                if result >= 0:
                    print(f"Wake word '{self.wakeword}' detected!")
                    break
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio_interface.terminate()


