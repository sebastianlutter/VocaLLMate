import os
import time
import asyncio
from dotenv import load_dotenv
from vocallmate.voice_activated_recording.va_factory import VoiceActivatedRecordingFactory

load_dotenv()

v=VoiceActivatedRecordingFactory()
print("Start listen for wake word")
recording = asyncio.run(v.listen_for_wake_word())
print(f"Got recording: frames={len(recording.getvalue())}")

