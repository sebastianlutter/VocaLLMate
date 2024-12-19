import os
import threading
from abc import ABC, abstractmethod
from typing import BinaryIO, List, Callable, Generator, AsyncGenerator


class AudioInterface(ABC):

    """
    A metaclass that combines ABCMeta and Singleton logic.
    This metaclass ensures that only one instance of any class using it is created.
    Only the first constructor call creates an instance, the other get the same reference
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # Check if an instance already exists
        if cls not in cls._instances:
            # Call ABCMeta.__call__ to create the instance (this respects ABC constraints)
            instance = super(AudioInterface, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]

    def __init__(self):
        self.frames_per_buffer = 1024
        self.sample_rate = 16000
        self.input_channels: int = 1
        self.bytes_per_frame = 2
        # Read environment variables
        self.audio_microphone_device = int(os.getenv('AUDIO_MICROPHONE_DEVICE', '-1'))
        if self.audio_microphone_device < 0:
            self.audio_microphone_device = None
        self.audio_playback_device = int(os.getenv('AUDIO_PLAYBACK_DEVICE', '-1'))
        if self.audio_playback_device < 0:
            self.audio_playback_device = None
        self.stop_signal_record = threading.Event()
        self.start_signal_record = threading.Event()

    @abstractmethod
    def list_devices(self) -> None:
        """
        List all available audio devices. This should display separate lists for input and output devices,
        along with relevant details such as device index, name, supported channels, and sample rates.
        """
        pass

    @abstractmethod
    def is_valid_device_index(self, index: int, input_device: bool = True) -> bool:
        """
        Check if the given device index is valid and can be used as an input or output device.

        :param index: The device index to validate.
        :param input_device: If True, checks for input capability; if False, checks for output capability.
        :return: True if the device index is valid for the requested direction, False otherwise.
        """
        pass

    @abstractmethod
    async def get_record_stream(self)  -> AsyncGenerator[bytes, None]:
        """
        Open a recording stream (or equivalent object) for capturing audio from the currently selected microphone device.

        :return: A stream or device handle suitable for reading raw audio data frames.
        :raises RuntimeError: If no valid microphone device is configured.
        """
        pass

    @abstractmethod
    def stop_recording(self):
        pass

    @abstractmethod
    def stop_playback(self):
        pass

    @abstractmethod
    def play_audio(self, sample_rate, audio_buffer):
        pass

    def config_str(self):
        return f'Soundcard device: microphone={self.audio_microphone_device}, playback: {self.audio_playback_device}'