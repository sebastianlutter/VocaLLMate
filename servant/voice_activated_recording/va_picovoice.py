import sys
import os
import pvporcupine
import numpy as np
from servant.voice_activated_recording.va_interface import VoiceActivationInterface

class PorcupineWakeWord(VoiceActivationInterface):
    def __init__(self):
        super().__init__()
        self.model_path = f'./{self.wakeword}_de_linux_v3_0_0.ppn'

        if not os.path.isfile(self.model_path):
            print(f"Picovoice model file is missing. Cannot find {self.model_path} for given wakeword {self.wakeword}")
            print("Please make an account and download one: https://picovoice.ai/")
            sys.exit(0)

        self.porcupine = pvporcupine.create(
            keyword_paths=[self.model_path],
            model_path='./porcupine_params_de.pv',
            sensitivities=[self.wakeword_threshold / 500.0],
            access_key=os.getenv('PICOVOICE_ACCESS_KEY')
        )

    async def listen_for_wake_word(self):
        try:
            print(f"Listening for wake word: {self.wakeword}")
            buffer = []
            async for chunk in self.soundcard.get_record_stream():
                # Convert raw PCM data to the format expected by Porcupine
                pcm = np.frombuffer(chunk, dtype=np.int16)
                buffer.extend(pcm)
                # Process in frames of the expected length
                while len(buffer) >= self.porcupine.frame_length:
                    frame = np.array(buffer[:self.porcupine.frame_length], dtype=np.int16)
                    buffer = buffer[self.porcupine.frame_length:]  # Remove processed samples
                    result = self.porcupine.process(frame)
                    if result >= 0:
                        print(f"Wake word '{self.wakeword}' detected!")
                        return
        finally:
            pass


