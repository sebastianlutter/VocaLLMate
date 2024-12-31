import os
import datetime
from fuzzywuzzy import process
from abc import ABC, abstractmethod

class LmmInterface(ABC):

    def __init__(self):
        self.available_mods=["",""]
        self.modus_selection_prompt="""


Beginne deine Antwort, indem du den gewählten Modus in GROSSBUCHSTABEN nennst (z. B. „CHEF“).
Gib danach exakt zwei kurze Sätze, abhängig vom gewählten Modus:
Wählst du CHEF, beschreibe eine schnelle Essensidee.
Wählst du DOCTOR, gib einen kurzen Gesundheitstipp.
Wählst du TRAVEL, empfehle ein kurzes Reiseziel.
Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text über die zwei Sätze hinaus.
Solltest du dich nicht an diese Vorgaben halten können, antworte mit: INVALID MODE
"""
        self.llm_endpoint=os.getenv('LLM_ENDPOINT', 'http://127.0.0.1:11434')
        self.llm_provider_model=os.getenv('LLM_PROVIDER_MODEL', 'llama3.2:3b')
        self.system_prompt=os.getenv('SYSTEM_PROMPT', )
        # add the current day, date and time to the prompt
        now = datetime.datetime.now(datetime.timezone.utc)
        # Print in the desired format, e.g., "Es ist Montag, der 30.12.2024 um 13:48 UTC"
        day_date_time=f"Es ist {now.strftime('%A')}, der {now.strftime('%d.%m.%Y')} um {now.strftime('%H:%M')} UTC. "
        self.system_prompt=f"{day_date_time}{self.system_prompt}"

        self.system_prompt=f"{self.system_prompt}"
    @abstractmethod
    def chat(self, text: str, stream: bool = False):
        pass

    def is_conversation_ending(self, sentence):
        # Define phrases that indicate the end of a conversation in both English and German
        end_phrases = [
            "stop chat", "exit", "bye", "finish",
            "halt stoppen", "chat beenden", "auf wiedersehen", "tschüss", "ende", "schluss",
        ]
        # Use fuzzy matching to find the closest match to the input sentence and get the match score
        highest_match = process.extractOne(sentence.lower(), end_phrases)
        # Define a threshold for deciding if the sentence means to end the conversation
        threshold = 80  # You can adjust the threshold based on testing
        # Check if the highest match score is above the threshold
        if highest_match[1] >= threshold:
            return True
        else:
            return False

    def config_str(self):
        return f'model: {self.llm_provider_model}, endpoint: {self.llm_endpoint}'