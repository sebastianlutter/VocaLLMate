import pyaudio
import wave
import os
import speech_recognition as sr
import numpy as np
from io import BytesIO
import time
from servant.voice_activation.va_interface import VoiceActivationInterface

class VoiceActivatedRecorder(VoiceActivationInterface):

    def __init__(self):
        super().__init__()
        self.wake_word = self.wakeword
        self.device_index = self.audio_microphone_device
        # Configurable delay before counting silence
        self.silence_lead_time = 2
        self.recognizer = sr.Recognizer()
        self.audio = pyaudio.PyAudio()  # Create an interface to PortAudio
        self.silence_threshold = self.wakeword_threshold

    def listen_for_wake_word(self):
        with sr.Microphone(device_index=self.device_index) as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("Listening for wake word...")
            while True:
                audio = self.recognizer.listen(source)
                try:
                    transcript = self.recognizer.recognize_google(audio).lower()
                    if self.wake_word in transcript:
                        print(f"Wake word '{self.wake_word}' detected. Starting recording...")
                        return self.start_recording()
                except sr.UnknownValueError:
                    print("Could not understand audio")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")

    def start_recording(self):
        print("Recording...")
        stream = self.audio.open(format=pyaudio.paInt16,
                                 channels=1,
                                 rate=16000,
                                 input=True,
                                 frames_per_buffer=1024)
        audio_frames = []
        silence_counter = 0
        record_start_time = time.time()

        while True:
            data = stream.read(1024, exception_on_overflow=False)
            if time.time() - record_start_time < self.silence_lead_time:
                audio_frames.append(data)
            else:
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
        return self.get_audio_buffer(audio_frames[:-30])

    def is_silence(self, data):
        audio_data = np.frombuffer(data, dtype=np.int16)
        mean_volume = np.mean(np.abs(audio_data))
        return mean_volume < self.silence_threshold

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

if __name__ == "__main__":
    recorder = VoiceActivatedRecorder(silence_lead_time=5)  # 5 seconds delay
    audio_buffer = recorder.listen_for_wake_word()
    if audio_buffer:
        # Save the buffer to a file for later use or verification
        with open("output_audio.wav", "wb") as f:
            f.write(audio_buffer.read())
        print("Audio buffer saved as 'output_audio.wav'.")
