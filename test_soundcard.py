import time
import io
import wave
import asyncio

import pyaudio
from dotenv import load_dotenv
from servant.audio_device.soundcard_factory import SoundcardFactory

load_dotenv()

duration = 5
# init the AudioDevice instance configured in .env
s=SoundcardFactory()
# the playback and recording thread are now running. Wait 3 seconds to test if record buffer queue works
# and later record start works well
print("Threads are running, waiting 3 seconds")
time.sleep(3)
print("Show available devices")
s.list_devices()

start_recording = time.time()
async def record_something(num: str):
    record_start_time = time.time()
    print("Record something the next 3 seconds")
    stream = s.get_record_stream()
    output_file = f"test_soundcard_{num}.wav"
    # Collect the WAV data from the stream into a BytesIO buffer
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        # Configure the WAV file parameters
        wav_file.setnchannels(s.input_channels)  # Mono audio
        wav_file.setsampwidth(2)  # 16-bit depth (2 bytes)
        wav_file.setframerate(s.sample_rate)  # Sample rate from SoundcardFactory
        # Write the chunks from the generator to the WAV file
        async for audio_chunk in stream:
            wav_file.writeframes(audio_chunk)
            # after 3 seconds stop the stream
            if time.time() - start_recording > duration:
                print(f"Stop recording now after {duration} seconds")
                s.stop_recording()
                break
    # Save the WAV buffer to a file
    with open(output_file, "wb") as f:
        f.write(wav_buffer.getvalue())
    # Pass the filled BytesIO object to the play_frames function
    wav_buffer.seek(0)  # Reset the buffer pointer to the beginning
    return wav_buffer

count=0
while True:
    print(f"Start:")
    count+=1
    wav_buffer = asyncio.run(record_something(str(count)))
    print(f"Recoding done: {len(wav_buffer.getvalue())}")
    time.sleep(2)

s.play_audio(s.sample_rate, wav_buffer.read())
print("Wait 5 seconds")
time.sleep(5.0)
print("Exit")