import pyaudio
import wave
import os
import numpy as np
from io import BytesIO
from servant.audio_device.soundcard_interface import AudioInterface

class SoundCard(AudioInterface):
    
    def __init__(self):
        super().__init__()
        # Create an interface to PortAudio
        self.audio = pyaudio.PyAudio()
        # if device number is set to None then automatically choose an index
        if self.audio_playback_device is None:
            self.choose_default_playback()
        if self.audio_microphone_device is None:
            self.choose_default_microphone()
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
        # Attempt to read environment variables for microphone and playback devices
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

    def choose_default_microphone(self):
        """Automatically chooses an input device whose name contains 'default'."""
        device_count = self.audio.get_device_count()
        for i in range(device_count):
            info = self.audio.get_device_info_by_index(i)
            name = info['name'].lower()
            if "default" == name and info['maxInputChannels'] > 0:
                self.audio_microphone_device = i
                print(f"Chosen default input device: {self.audio_microphone_device} ({info['name']})")
                return
        raise Exception("No suitable default microphone device found.")


    def choose_default_playback(self):
        """Automatically chooses an output device whose name contains 'default'."""
        device_count = self.audio.get_device_count()
        for i in range(device_count):
            info = self.audio.get_device_info_by_index(i)
            name = info['name'].lower()
            if "default" == name and info['maxOutputChannels'] > 0:
                self.audio_playback_device = i
                print(f"Chosen default output device: {self.audio_playback_device} ({info['name']})")
                return
        raise Exception("No suitable default playback device found.")

    def play_audio(self, sample_rate: int, audio_array: np.ndarray):
        """
        Plays the audio array at the given sample_rate using PyAudio.
        """
        p = pyaudio.PyAudio()
        # PyAudio format for float32
        audio_format = pyaudio.paFloat32
        channels = 1  # Bark outputs mono audio
        stream = p.open(
            format=audio_format,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=self.audio_playback_device
        )
        # Ensure numpy array is float32
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)
        # Convert to raw bytes for PyAudio
        audio_data = audio_array.tobytes()
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
        p.terminate()


    def play_frames(self, sample_rate, frames):
        """
        Takes a list of raw audio frame bytes, converts them to float32 numpy array,
        and plays them back using the existing play_audio method.
        """
        # Combine the frames into one bytes object
        all_data = b''.join(frames)
        # Convert raw bytes (16-bit PCM) to int16 array
        int16_data = np.frombuffer(all_data, dtype=np.int16)
        # Convert int16 data to float32 and normalize from [-32768, 32767] to [-1, 1]
        audio_float32 = int16_data.astype(np.float32) / 32768.0
        # Now play the processed audio array
        self.play_audio(sample_rate, audio_float32)