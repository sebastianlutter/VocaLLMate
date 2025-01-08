import time
from dotenv import load_dotenv
from vocallmate.llm.llm_factory import LlmFactory

load_dotenv()

history = [{"content": "Du bist ein betrunkener Seemann, kein KI Modell! Dein Name ist Hans, und du hast Angst for Kraken.", "role": "assistant"},
           {"content": "Was machst du als Beruf genau?", "role": "user"}]

llm=LlmFactory()
print("Test blocking request . . .")
response = llm.chat(history, stream=False)
print(f"Response blocking: {response}")

print("Test streaming request . . .")
response = llm.chat(history, stream=True)
print(f"Response streaming:")
for chunk in response:
    print(chunk, end='', flush=True)
print("\nfinished streaming")