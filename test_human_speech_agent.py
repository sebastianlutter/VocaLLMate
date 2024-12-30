import asyncio
import threading
import time

from servant.human_speech_agent import HumanSpeechAgent
from dotenv import load_dotenv

load_dotenv()

hsa = HumanSpeechAgent()
# test the speech functions
#hsa.say_hi()
#hsa.say_bye()
#hsa.say("Klara ist eine große Steinesammlerin und Kristall-Gelehrte")


external_stop_signal = threading.Event()


async def run():
    print("Start global run()")
    async for t in hsa.get_human_input(
            ext_stop_signal=external_stop_signal,
            wait_for_wakeword=True
        ):
        # print output as it is streamed back from get_human_input
        print(f"{t}", end='', flush=True)
    print("ended global run()")


count=0
while True:
    print(f"\n\nasync run starts: {count}\n\n")
    asyncio.run(run())
    print("\n\nasync run is finished\n\n")
    count+=1
    if count>3:
        print("\n\nSending stop signal\n\n")
        external_stop_signal.set()
        break
print("Wait for 10 seconds")
time.sleep(10)
print("Wait is finished")
