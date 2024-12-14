import queue
import time
import os
from threading import Thread
from abc import ABC, abstractmethod

import random


class TextToSpeechInterface(ABC):

    def __init__(self):
        self.tts_endpoint = os.getenv('TTS_ENDPOINT', 'http://127.0.0.1:8001/v1')
        # a queue for the sentences to say
        self.queue = queue.Queue()
        # Create a thread for the speak_loop
        self.speak_thread = Thread(target=self.speak_loop)
        self.speak_thread.daemon = True  # Set thread as daemon for clean termination
        self.speak_thread.start()  # Start the speak_loop thread
        self.still_speaking = False

    def speak(self, text: str):
        # clean the text from all special chars (markdown etc)
        self.queue.put(text)
        self.still_speaking = False

    @abstractmethod
    def speak_sentence(self, sentence: str):
        pass

    def speak_loop(self):
        t_old = None
        while True:
            sentence = self.queue.get()
            self.still_speaking = True
            #print(f"Got sentence: {sentence}")
            t_new = self.speak_sentence(sentence)
            if t_old is not None:
                t_old.join()
            t_new.start()
            t_old = t_new
            if self.queue.empty():
                self.still_speaking = False
            # wait to have a small gap after each sentence
            #time.sleep(1.2)

    def config_str(self):
        return f'endpoint: {self.tts_endpoint}'