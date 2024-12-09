import queue
import time
import os
from threading import Thread
from abc import ABC, abstractmethod

import random


class TextToSpeechInterface(ABC):

    def __init__(self):
        self.tts_endpoint = os.getenv('TTS_ENDPOINT', 'local')
        # a queue for the sentences to say
        self.queue = queue.Queue()
        # Create a thread for the speak_loop
        self.speak_thread = Thread(target=self.speak_loop)
        self.speak_thread.daemon = True  # Set thread as daemon for clean termination
        self.speak_thread.start()  # Start the speak_loop thread

    def speak(self, text: str):
        # clean the text from all special chars (markdown etc)
        self.queue.put(text)

    @abstractmethod
    def speak_sentence(self, sentence: str):
        pass

    def speak_loop(self):
        t_old = None
        while True:
            sentence = self.queue.get()
            print(f"Got sentence: {sentence}")
            t_new = self.speak_sentence(sentence)
            if t_old is not None:
                t_old.join()
            t_new.start()
            t_old = t_new
            # wait to have a small gap after each sentence
            #time.sleep(1.2)

    def config_str(self):
        return f'endpoint: {self.tts_endpoint}'