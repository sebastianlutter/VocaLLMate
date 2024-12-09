import time
from dotenv import load_dotenv
from servant.tts.tts_factory import TtsFactory

load_dotenv()

s=TtsFactory()
s.speak("Ich bin ein langer Satz mit vielen Worten.")
s.speak("Ich nicht.")

time.sleep(5)

