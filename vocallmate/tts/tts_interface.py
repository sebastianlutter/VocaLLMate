import os
import threading
import queue
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Type
from vocallmate.audio_device.soundcard_factory import SoundcardFactory

T = TypeVar('T', bound='TextToSpeechInterface')

class TextToSpeechInterface(ABC):
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        # Protect against multiple initializations if someone tries to create another instance
        if getattr(self, "_initialized", False):
            return
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.tts_endpoint = os.getenv('TTS_ENDPOINT', 'http://127.0.0.1:8001/v1')
        self._initialized = True
        self._sentence_queue = queue.Queue()
        self.stop_signal = threading.Event()

        # Condition and state to track processing
        self._condition = threading.Condition()
        self._speaking = False

        # Start background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # reference to the soundcard
        self.soundcard = SoundcardFactory()

    @abstractmethod
    def render_sentence(self, sentence: str, store_file_name: str, output_format: str):
        """
        This function should store the TTS result as mp3 or wav file
        """
        pass

    @abstractmethod
    def speak_sentence(self, sentence: str):
        """
        Concrete implementations must provide how the sentence should be spoken.
        """
        pass

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        """
        Implements a singleton access method.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def _run(self):
        """
        Background thread continuously pulls sentences from the queue and speaks them.
        Stops when stop_signal is set.
        """
        while True:
            if self.stop_signal.is_set():
                self.clear_queue()
                break

            try:
                sentence = self._sentence_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if self.stop_signal.is_set():
                self.clear_queue()
                break

            # Indicate we are now speaking
            with self._condition:
                self._speaking = True
            logging.debug(f"SPEAK SENTENCE: {sentence}. Remaining in queue {self._sentence_queue._qsize()}")
            self.speak_sentence(sentence)
            # Finished speaking
            with self._condition:
                self._speaking = False
                self._condition.notify_all()

    def clear_queue(self):
        with self._sentence_queue.mutex:
            self._sentence_queue.queue.clear()
        # Notify if we are waiting for done
        with self._condition:
            self._condition.notify_all()

    def speak(self, sentence: str):
        """
        Public method to enqueue a sentence to be spoken.
        """
        logging.debug(f"speak: {sentence}")
        if not self.stop_signal.is_set():
            self._sentence_queue.put(sentence)
            # Notify condition in case someone is waiting and we want them aware queue changed
            with self._condition:
                self._condition.notify_all()

    def set_stop_signal(self):
        """
        Sets the stop signal event, clears the queue, and waits for the thread to finish.
        """
        self.stop_signal.set()
        self.soundcard.stop_playback()
        if self._thread.is_alive():
            self._thread.join()

    def clear_stop_signal(self):
        """
        Clears the stop signal and restarts the background thread.
        """
        self.soundcard.stop_signal_playback.clear()
        if self.stop_signal.is_set():
            self.stop_signal.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def config_str(self):
        return f'endpoint: {self.tts_endpoint}'

    def wait_until_done(self):
        """
        Blocks until the queue is empty and no sentence is currently being spoken.
        """
        with self._condition:
            while not self._sentence_queue.empty() or self._speaking:
                self._condition.wait()