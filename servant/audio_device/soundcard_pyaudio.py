import pyaudio
import wave
import os
from io import BytesIO
from servant.audio_device.soundcard_interface import AudioInterface

class SoundCard(AudioInterface):
    def __init__(self):
        # Create an interface to PortAudio
        self.audio = pyaudio.PyAudio()
        self.frames_per_buffer = 1024

        # Attempt to read environment variables for microphone and playback devices
        # Fallback to 0 if not set.
        self.audio_microphone_device = int(os.getenv('AUDIO_MICROPHONE_DEVICE', '0'))
        if self.audio_microphone_device < 0:
            self.audio_playback_device = None
        self.audio_playback_device = int(os.getenv('AUDIO_PLAYBACK_DEVICE', '0'))
        if self.audio_playback_device < 0:
            self.audio_playback_device = None
        # Validate microphone device index
        if not self.is_valid_device_index(self.audio_microphone_device, input_device=True):
            print("Available devices:")
            self.list_devices()
            raise Exception(f"Error: The microphone device index '{self.audio_microphone_device}' is invalid or not available.")
        # Validate playback device index
        if not self.is_valid_device_index(self.audio_playback_device, input_device=False):
            print("Available devices:")
            self.list_devices()
            raise Exception(f"Error: The playback device index '{self.audio_playback_device}' is invalid or not available.")
        print("Available devices:")
        self.list_devices()
        print(f"Loading device: microphone={self.audio_microphone_device}, playback={self.audio_playback_device}")
        # Print chosen devices
        print(f"Chosen Microphone Device Index: {self.audio_microphone_device}")
        print(f"Chosen Playback Device Index: {self.audio_playback_device}")

    def list_devices(self):
        """List all microphone (input) and playback (output) devices in separate well-formed tables."""
        device_count = self.audio.get_device_count()

        # Separate devices into microphones and playback devices
        microphone_devices = []
        playback_devices = []
        for i in range(device_count):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                microphone_devices.append((i, info))
            if info['maxOutputChannels'] > 0:
                playback_devices.append((i, info))

        # Define table headers
        headers = ["Index", "Name", "Input Channels", "Output Channels", "Default Sample Rate"]

        # Print Microphone Devices
        print("\nMicrophone (Input) Devices:")
        print("-" * 85)
        print(f"| {' | '.join(headers)} |")
        print("-" * 85)
        for idx, info in microphone_devices:
            print(f"| {idx:<5} | {info['name']:<30} | {info['maxInputChannels']:<14} | {info['maxOutputChannels']:<15} | {info['defaultSampleRate']:<19} |")
        print("-" * 85)

        # Print Playback Devices
        print("\nPlayback (Output) Devices:")
        print("-" * 85)
        print(f"| {' | '.join(headers)} |")
        print("-" * 85)
        for idx, info in playback_devices:
            print(f"| {idx:<5} | {info['name']:<30} | {info['maxInputChannels']:<14} | {info['maxOutputChannels']:<15} | {info['defaultSampleRate']:<19} |")
        print("-" * 85)
        print()  # Extra newline for readability


    def is_valid_device_index(self, index, input_device=True):
        """Check if the given device index is valid and can be used as an input or output device."""
        if index is None or index < 0 or index >= self.audio.get_device_count():
            return False
        info = self.audio.get_device_info_by_index(index)
        if input_device and info['maxInputChannels'] < 1:
            return False
        if not input_device and info['maxOutputChannels'] < 1:
            return False
        return True

    def get_record_stream(self):
        """Open a recording stream using the validated microphone device index if available."""
        if self.audio_microphone_device is None:
            raise RuntimeError("No valid microphone device configured. Please set a valid device index.")
        return self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=self.frames_per_buffer,
            input_device_index=self.audio_microphone_device
        )

    def get_audio_buffer(self, frames):
        """Get a buffer with audio data as a WAV in-memory stream."""
        byte_io = BytesIO()
        with wave.open(byte_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        byte_io.seek(0)  # Reset buffer pointer to the beginning
        return byte_io


