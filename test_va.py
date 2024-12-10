import time
from dotenv import load_dotenv
from servant.voice_activated_recording.va_factory import VoiceActivatedRecordingFactory

load_dotenv()

v=VoiceActivatedRecordingFactory()
print("Start listen for wake word")
recording = v.listen_for_wake_word()
print(f"Got recording: frames={len(recording.getvalue())}")

