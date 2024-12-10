import speech_recognition as sr
import json
from servant.voice_activated_recording.va_interface import VoiceActivationInterface
import io
import wave
import os
import requests

class WhisperActivated(VoiceActivationInterface):

    def __init__(self):
        super().__init__()
        self.wake_word = self.wakeword
        self.stt_endpoint = os.getenv('STT_ENDPOINT', 'http://127.0.0.1:8000/v1/audio/transcriptions')

    def listen_for_wake_word(self):
        # Parameters for recording (adjust as needed)
        sample_rate = 16000  # e.g. 16kHz
        channels = 1          # e.g. mono
        sample_width = 2      # e.g. 16-bit audio
        chunk_size = 1024     # number of frames per read
        chunks_per_iteration = 50  # how many chunks to accumulate before checking

        print("Listening for wake word...")

        # Continuously read from the microphone until wake word is detected
        with self.soundcard.get_record_stream() as stream:
            while True:
                # Read a portion of audio data
                frames = []
                for _ in range(chunks_per_iteration):
                    # `stream.read()` should return raw audio frames
                    data = stream.read(chunk_size)
                    if not data:
                        # No data means stream ended unexpectedly
                        break
                    frames.append(data)

                if not frames:
                    # If we didn't get any frames, continue or break as appropriate
                    continue

                # Create a WAV buffer in-memory
                audio_buffer = io.BytesIO()
                with wave.open(audio_buffer, 'wb') as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(frames))
                audio_buffer.seek(0)

                # Send the recorded chunk to the STT service
                files = {
                    'file': ('audio.wav', audio_buffer, 'audio/wav'),
                    'stream': (None, 'false')
                }
                response = requests.post(self.stt_endpoint, files=files)
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    print("Failed to decode JSON from response")
                    print("Response was:", response.text)
                    continue

                transcript = data.get("text", "").lower()

                # Check if the wake word is in the transcript
                if self.wake_word.lower() in transcript:
                    print(f"Wake word '{self.wake_word}' detected. Starting recording...")
                    return self.start_recording()
