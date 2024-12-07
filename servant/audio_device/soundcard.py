import pyaudio
import wave
import os
from io import BytesIO

class SoundCard:

    def __init__(self):
        # Create an interface to PortAudio
        self.audio = pyaudio.PyAudio()
        self.audio_microphone_device = int(os.getenv('AUDIO_MICROPHONE_DEVICE'))
        if self.audio_microphone_device < 0:
            self.audio_microphone_device = None
        self.device_index = self.audio_microphone_device
        self.frames_per_buffer = 1024

    def get_record_stream(self):
        return self.audio.open(format=pyaudio.paInt16,
                                 channels=1,
                                 rate=16000,
                                 input=True,
                                 frames_per_buffer=self.frames_per_buffer)

    def get_audio_buffer(self, frames):
        """Get a buffer with audio data."""
        byte_io = BytesIO()
        with wave.open(byte_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        byte_io.seek(0)  # Reset buffer pointer to the beginning
        return byte_io

