import asyncio
import threading

from servant.human_speech_agent import HumanSpeechAgent
from dotenv import load_dotenv

load_dotenv()

hsa = HumanSpeechAgent()
# test the speech functions
hsa.say_hi()
hsa.say_bye()
hsa.say("Klara ist eine große Steinsammlering und Kristall Gelehrte")


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


asyncio.run(run())
print("async run is finished")


