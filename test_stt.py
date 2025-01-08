import wave
import time
from dotenv import load_dotenv
from io import BytesIO
from vocallmate.stt.stt_factory import SttFactory

load_dotenv()

channel=1
format_bytes=2 #pyaudio.paInt16
sample_rate=16000
frames_per_buffer=1024

def load_wav_as_frames(file_path):
    """
    Given a WAV file on disk, this function reads it and returns the raw frames
    in a list, similar to what would be returned by PyAudio's stream.read().
    It reads the file in chunks of self.frames_per_buffer frames.
    """
    frames = []
    with wave.open(file_path, 'rb') as wf:
        # Confirm format matches expectations (optional checks)
        if wf.getframerate() != sample_rate:
            print(f"Warning: WAV file sample rate ({wf.getframerate()}) differs from expected ({self.sample_rate}).")
        if wf.getnchannels() != 1:
            print("Warning: WAV file is not mono. Expected 1 channel.")
        data = wf.readframes(frames_per_buffer)
        while data:
            frames.append(data)
            data = wf.readframes(frames_per_buffer)
    return frames

def load_wav_as_blob(file_path):
    byte_io = BytesIO()
    with open(file_path, 'rb') as f:
        byte_io.write(f.read())
    byte_io.seek(0)
    return byte_io

# Test with wave file
s=SttFactory()
file = 'stt-stack/audio.wav'
print(f"Loading wav file {file}")
audio_buffer = load_wav_as_blob(file)
print("Transcribe audio_buffer")
transcript = s.transcribe(audio_buffer)
print(f"Got text: {transcript}")


