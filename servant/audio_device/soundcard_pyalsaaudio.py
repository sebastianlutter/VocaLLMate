import os
import wave
from io import BytesIO
import alsaaudio
from servant.audio_device.soundcard_interface import AudioInterface

class SoundCard(AudioInterface):
    def __init__(self):
        super().__init__()
        self.frames_per_buffer = 1024
        self.devices = self._enumerate_devices()
        print("Available devices:")
        self.list_devices()
        print(f"Loading device: microphone={self.audio_microphone_device}, playback={self.audio_playback_device}")
        print(f"Chosen Microphone Device Index: {self.audio_microphone_device}")
        print(f"Chosen Playback Device Index: {self.audio_playback_device}")

    def _enumerate_devices(self):
        """
        Enumerate ALSA PCM devices and check which ones support input and/or output.
        We'll try to open each device in input and output mode to see what it's capable of.
        """
        device_names = alsaaudio.pcms()  # returns a list of device names like ['default', 'sysdefault', 'hw:0,0', ...]
        devices = []
        for name in device_names:
            is_input = self._can_open_device(name, alsaaudio.PCM_CAPTURE)
            is_output = self._can_open_device(name, alsaaudio.PCM_PLAYBACK)
            # We won't be able to get exact input/output channels or default sample rate easily.
            # We'll set them to 1 if supported, as a placeholder.
            input_channels = 1 if is_input else 0
            output_channels = 1 if is_output else 0
            # Assume a default sample rate of 44100.0 if the device can be opened.
            default_sample_rate = "44100.0" if (is_input or is_output) else "N/A"
            if is_input or is_output:
                devices.append({
                    'name': name,
                    'is_input': is_input,
                    'is_output': is_output,
                    'input_channels': input_channels,
                    'output_channels': output_channels,
                    'default_sample_rate': default_sample_rate
                })
        return devices

    def _can_open_device(self, name, mode):
        """
        Try to open the device in the given mode (PCM_CAPTURE or PCM_PLAYBACK).
        Return True if successful, False otherwise.
        """
        try:
            pcm = alsaaudio.PCM(mode=mode, device=name)
            # Try minimal configuration
            pcm.setrate(16000)
            pcm.setchannels(1)
            pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            pcm.setperiodsize(self.frames_per_buffer)
            return True
        except Exception:
            return False

    def list_devices(self):
        """List all microphone (input) and playback (output) devices in separate well-formed tables."""
        microphone_devices = [(i, d) for i, d in enumerate(self.devices) if d['is_input']]
        playback_devices = [(i, d) for i, d in enumerate(self.devices) if d['is_output']]

        headers = ["Index", "Name", "Input Channels", "Output Channels", "Default Sample Rate"]

        print("\nMicrophone (Input) Devices:")
        print("-" * 85)
        print(f"| {' | '.join(headers)} |")
        print("-" * 85)
        for idx, info in microphone_devices:
            print(f"| {idx:<5} | {info['name']:<30} | {info['input_channels']:<14} | {info['output_channels']:<15} | {info['default_sample_rate']:<19} |")
        print("-" * 85)

        print("\nPlayback (Output) Devices:")
        print("-" * 85)
        print(f"| {' | '.join(headers)} |")
        print("-" * 85)
        for idx, info in playback_devices:
            print(f"| {idx:<5} | {info['name']:<30} | {info['input_channels']:<14} | {info['output_channels']:<15} | {info['default_sample_rate']:<19} |")
        print("-" * 85)
        print()  # Extra newline for readability

    def is_valid_device_index(self, index, input_device=True):
        """Check if the given device index is valid and can be used as an input or output device."""
        if index is None or index < 0 or index >= len(self.devices):
            return False
        dev = self.devices[index]
        return dev['is_input'] if input_device else dev['is_output']

    def get_record_stream(self):
        """Open a recording 'stream' (PCM object) using the validated microphone device index if available."""
        if self.audio_microphone_device is None:
            raise RuntimeError("No valid microphone device configured. Please set a valid device index.")

        device_name = self.devices[self.audio_microphone_device]['name']
        pcm = alsaaudio.PCM(mode=alsaaudio.PCM_CAPTURE, device=device_name)
        pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        pcm.setchannels(1)
        pcm.setrate(16000)
        pcm.setperiodsize(self.frames_per_buffer)
        return pcm

    def get_audio_buffer(self, frames):
        """Get a buffer with audio data as a WAV in-memory stream."""
        byte_io = BytesIO()
        with wave.open(byte_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # S16_LE is 16 bits = 2 bytes
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
        byte_io.seek(0)  # Reset buffer pointer to the beginning
        return byte_io
