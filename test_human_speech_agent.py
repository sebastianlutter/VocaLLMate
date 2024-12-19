import asyncio
from servant.human_speech_agent import HumanSpeechAgent
from dotenv import load_dotenv

load_dotenv()

hsa = HumanSpeechAgent()

async def run():
    print("Start global run()")
    async for t in hsa.get_human_input(
            should_continue=lambda: True,
            wait_for_wakeword=True
        ):
        # print output as it is streamed back from get_human_input
        print(f"{t}", end='', flush=True)
    print("ended global run()")


asyncio.run(run())
print("async run is finished")


