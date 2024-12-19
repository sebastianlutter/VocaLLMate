import time
import io
import wave
from dotenv import load_dotenv
from servant.audio_device.soundcard_factory import SoundcardFactory

load_dotenv()

s=SoundcardFactory()
print("Show available devices")
s.list_devices()
record_start_time = time.time()
print("Record something for 3 seconds")
stream = s.get_record_stream(lambda: time.time() - record_start_time < 3.0)
output_file = "test_soundcard.wav"
# Collect the WAV data from the stream into a BytesIO buffer
wav_buffer = io.BytesIO()

with wave.open(wav_buffer, 'wb') as wav_file:
    # Configure the WAV file parameters
    wav_file.setnchannels(s.input_channels)  # Mono audio
    wav_file.setsampwidth(2)  # 16-bit depth
    wav_file.setframerate(s.sample_rate)  # Sample rate from SoundcardFactory
    # Write the chunks from the generator to the WAV file
    for audio_chunk in stream:
        wav_file.writeframes(audio_chunk)
# Save the WAV buffer to a file
with open(output_file, "wb") as f:
    f.write(wav_buffer.getvalue())

# Pass the filled BytesIO object to the play_frames function
wav_buffer.seek(0)  # Reset the buffer pointer to the beginning
s.play_frames(s.sample_rate, wav_buffer.read())