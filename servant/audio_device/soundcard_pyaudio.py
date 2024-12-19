import time
from typing import Generator, Callable, AsyncGenerator
import queue
import threading
import pyaudio
import wave
import os
import io
import numpy as np
from io import BytesIO
from servant.audio_device.soundcard_interface import AudioInterface

class SoundCard(AudioInterface):
    
    def __init__(self):
        super().__init__()
        self.sample_format: int = pyaudio.paInt16
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
        # Setup for queued playback
        self.playback_queue = queue.Queue()
        self.playback_thread = None
        self.playback_thread_lock = threading.Lock()
        self.playback_stream = None
        # stop signals
        self.stop_signal_record = threading.Event()
        self.stop_signal_playback = threading.Event()

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

    async def get_record_stream(self)  -> AsyncGenerator[bytes, None]:
        """Open a recording stream using the validated microphone device index if available."""
        if self.audio_microphone_device is None:
            raise RuntimeError("No valid microphone device configured. Please set a valid device index.")
        # reset stop signal
        self.stop_signal_record.clear()
        stream = self.audio.open(
                format=self.sample_format,
                channels=self.input_channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.frames_per_buffer,
                input_device_index=self.audio_microphone_device
            )
        try:
            while not self.stop_signal_record.is_set():
                # Read audio data from the microphone
                yield stream.read(self.frames_per_buffer, exception_on_overflow=False)
            print("soundcard_pyaudio.get_record_stream: while loop reading from microphone stopped")
        finally:
            stream.stop_stream()
            stream.close()

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

    def _playback_worker(self):
        """
        This worker runs in a separate thread, pulling items from the queue and playing them.
        It opens the playback stream when it encounters the first audio item and closes it after
        the queue is empty and stop_signal is set or no more items remain.
        """
        try:
            stream = None
            while not self.stop_signal_playback.is_set():
                try:
                    # Wait for item with a timeout, so we can check stop_signal periodically
                    item = self.playback_queue.get(timeout=0.01)
                except queue.Empty:
                    # No items currently, check if we should stop
                    # Write a small silence buffer if the stream is open
                    if stream is not None and not stream.is_stopped():
                        silence = (np.zeros(22500, dtype=np.int32)).tobytes()
                        stream.write(silence)
                    continue
                if item is None:  # A sentinel to stop
                    break
                sample_rate, audio_array = item
                if stream is None:
                    stream = self.audio.open(
                        format=pyaudio.paFloat32,
                        channels=1,
                        rate=sample_rate,
                        output=True,
                        output_device_index=self.audio_playback_device
                    )
                    stream.start_stream()
                # Ensure correct dtype
                if audio_array.dtype != np.float32:
                    audio_array = audio_array.astype(np.float32)
                audio_data = audio_array.tobytes()
                # Write data to stream
                stream.write(audio_data)
                self.playback_queue.task_done()
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()

    def start_playback_thread(self):
        """Start the worker thread if not already started."""
        with self.playback_thread_lock:
            if self.playback_thread is None or not self.playback_thread.is_alive():
                self.stop_signal_playback.clear()
                self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
                self.playback_thread.start()

    def play_audio(self, sample_rate: int, audio_array: np.ndarray):
        """
        Enqueue the audio array at the given sample_rate for playback.
        The actual playback happens in a separate worker thread.
        """
        self.start_playback_thread()
        self.playback_queue.put((sample_rate, audio_array))

    def stop_playback(self):
        """
        Immediately stop playback, empty the queue, stop the worker thread, and set
        everything in a safe state.
        """
        self.stop_signal_playback.set()
        # Clear the queue
        while not self.playback_queue.empty():
            try:
                self.playback_queue.get_nowait()
                self.playback_queue.task_done()
            except queue.Empty:
                break
        # Push a sentinel to ensure the thread stops
        self.playback_queue.put(None)
        if self.playback_thread is not None:
            self.playback_thread.join()
            self.playback_thread = None

    def stop_recording(self):
        self.stop_signal_record.set()

