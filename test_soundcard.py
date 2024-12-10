import time
from dotenv import load_dotenv
from servant.audio_device.soundcard_factory import SoundcardFactory

load_dotenv()

s=SoundcardFactory()
print("Show available devices")
s.list_devices()
print("Record something for 3 seconds")
stream = s.get_record_stream()
audio_frames = []
record_start_time = time.time()
while True:
    data = stream.read(s.frames_per_buffer, exception_on_overflow=False)
    if time.time() - record_start_time < 3.0:
        audio_frames.append(data)
    else:
        break
print("Playback recording:")
s.play_frames(s.sample_rate, audio_frames)
print("Finished")
