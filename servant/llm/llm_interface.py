import os
from fuzzywuzzy import process
from abc import ABC, abstractmethod

class LmmInterface(ABC):

    def __init__(self):
        self.llm_endpoint=os.getenv('LLM_ENDPOINT', 'http://127.0.0.1:11434')
        self.llm_provider_model=os.getenv('LLM_PROVIDER_MODEL', 'llama3.2:1b')
        self.system_prompt=os.getenv('SYSTEM_PROMPT', 'Beantworte die Fragen als freundlicher und zuvorkommender Helfer. Antworte maximal mit 1 bis 3 kurzen Sätzen und stelle Gegenfragen wenn der Sachverhalt unklar ist.')

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