import time
from dotenv import load_dotenv
from vocallmate.tts.tts_factory import TtsFactory

load_dotenv()

s=TtsFactory()
#msg = "Mein Herr, ich habe von diesen Dingen keine Ahnung!"
#s.speak(msg)
with open('test.txt') as f:
    for line in f.readlines():
        s.speak(line)
print("")
s.wait_until_done()

#s.speak("Ich nicht.")
print("Start sleep 5")
time.sleep(5)
print("set stop signal")
s.set_stop_signal()
print("wait until done")

print("wait another 10 sec")
time.sleep(10)
print("done")
