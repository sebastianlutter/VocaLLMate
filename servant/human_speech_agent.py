import random
import threading
import time
import os
import io
import hashlib
from typing import Callable, Generator, AsyncGenerator, Tuple
from servant.audio_device.soundcard_factory import SoundcardFactory
from servant.stt.stt_factory import SttFactory
from servant.tts.tts_factory import TtsFactory
from servant.voice_activated_recording.va_factory import VoiceActivatedRecordingFactory
from tqdm import tqdm
from pydub import AudioSegment
import soundfile as sf

class HumanSpeechAgent:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create new instance
                    cls._instance = super(HumanSpeechAgent, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure __init__ only runs once per singleton instance
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.soundcard = SoundcardFactory()
        self.voice_activator = VoiceActivatedRecordingFactory()
        self.tts_provider = TtsFactory()
        self.silence_lead_time = 2
        self.max_recording_time = 15
        self.stt_provider = SttFactory()
        self.stop_signal = threading.Event()
        self.hi_choices = [
            'ja, hi', 'schiess los!',
            'was gibts?', 'hi, was?',
            'leg los!', 'was willst du?',
            'sprechen Sie', 'jo bro',
            "Moin!", "Na?",
        ]
        self.bye_choices = [
            "Auf Wiedersehen!", "Mach’s gut!", "Bis zum nächsten Mal!", "Tschüss!", "Ciao!", "Adieu!",
            "Schönen Tag noch!",
            "Bis bald!", "Pass auf dich auf!", "Bleib gesund!", "Man sieht sich!", "Bis später!", "Bis dann!",
            "Gute Reise!",
            "Viel Erfolg noch!", "Danke und tschüss!", "Alles Gute!", "Bis zum nächsten Treffen!",
            "Leb wohl!"
        ]
        self.init_greetings = [
            "Hallo!", "Hi!", "Hey!", "Guten Tag!", "Guten Morgen!",
            "Guten Abend!", "Grüß dich!", "Servus!", "Hallöchen!",
            "Hi, wie geht's?", "Schön dich zu sehen!", "Hallo und willkommen!",
            "Freut mich, dich zu treffen!", "Hallo zusammen!", "Hallo, mein Freund!",
            "Guten Tag, wie kann ich helfen?", "Willkommen!", "Hallo an alle!",
            "Hallihallo!", "Herzlich willkommen!", "Hallo, schön dich hier zu haben!",
            "Moin moin!", "Hey, alles klar?", "Hallo, schön dich kennenzulernen!",
            "Hallo, wie läuft's?", "Grüß Gott!", "Einen schönen Tag!", "Schön, dass du da bist!"
        ]
        self.explain_sentence = "Sag das wort computer um zu starten."
        self._warmup_cache()

    def say_init_greeting(self):
        hi_phrase = random.choice(self.init_greetings)
        mp3_path = self._get_cache_file_name(hi_phrase)
        sample_rate, audio_buffer = self._load_mp3_to_wav_bytesio(mp3_path)
        self.soundcard.play_audio(sample_rate, audio_buffer)
        while True:
            if self.soundcard.playback_queue.all_tasks_done:
                break
            time.sleep(0.5)

    def say_hi(self):
        hi_phrase = random.choice(self.hi_choices)
        mp3_path = self._get_cache_file_name(hi_phrase)
        sample_rate, audio_buffer = self._load_mp3_to_wav_bytesio(mp3_path)
        self.tts_provider.set_stop_signal()
        self.tts_provider.wait_until_done()
        self.tts_provider.clear_stop_signal()
        self.soundcard.play_audio(sample_rate, audio_buffer)

    def say_bye(self, message: str = ''):
        bye_phrase = random.choice(self.bye_choices)
        mp3_path = self._get_cache_file_name(bye_phrase)
        sample_rate, audio_buffer = self._load_mp3_to_wav_bytesio(mp3_path)
        self.tts_provider.set_stop_signal()
        self.tts_provider.clear_stop_signal()
        if message != '':
            self.tts_provider.speak(message)
        self.tts_provider.wait_until_done()
        self.soundcard.play_audio(sample_rate, audio_buffer)


    def say(self, message: str):
        self.tts_provider.speak(message)

    def skip_all_and_say(self, message: str):
        # first skip all speaking tasks
        self.tts_provider.set_stop_signal()
        self.tts_provider.wait_until_done()
        self.tts_provider.clear_stop_signal()
        if not message == '':
            self.tts_provider.speak(message)

    def block_until_talking_finished(self):
        return self.tts_provider.wait_until_done()

    async def get_human_input(self, ext_stop_signal: threading.Event, wait_for_wakeword: bool = True) -> AsyncGenerator[str, None]:
        if wait_for_wakeword:
            self.voice_activator.listen_for_wake_word()

        def should_continue_ws():
            external_should_continue = not ext_stop_signal.is_set()
            b = (not self.stop_signal.is_set()) and external_should_continue
            if not b:
                print(f"should_continue_ws={b} | (not stop_signal.is_set()={self.stop_signal.is_set()}) and external_should_continue={external_should_continue}")
            return b

        def on_close_ws_callback():
            print("on-close websocket callback:")
            self.stop_signal.set()

        async for text in self.stt_provider.transcribe_stream(
            audio_stream=self.start_recording(),
            websocket_on_close=on_close_ws_callback,
            websocket_on_open=self.say_hi
        ):
            yield text
        print("END OF: get_human_input")

    async def start_recording(self) -> AsyncGenerator[bytes, None]:
        print("Recording...")
        silence_counter = 0
        record_start_time = time.time()

        def continue_recording():
            stop_now_bool = self.stop_signal.is_set()
            silence_detected = silence_counter > 30
            silence_lead_time_passed = time.time() - record_start_time < self.silence_lead_time
            max_time_passed = time.time() - record_start_time > self.max_recording_time
            b = not ((silence_detected and silence_lead_time_passed) or max_time_passed or stop_now_bool)
            if not b:
                print("Stop recording...")
                print(f"should_continue= not ((silence_detected={silence_detected} and silence_lead_time_passed={silence_lead_time_passed}) or max_time_passed={max_time_passed} or stop_now={stop_now_bool})")
            return b

        async for wav_chunk in self.soundcard.get_record_stream():
            yield wav_chunk
        print("END OF: start_recording")

    def _warmup_cache(self):
        # Ensure the tts_cache directory exists
        os.makedirs("tts_cache", exist_ok=True)
        # Pre-render all hi and bye choices to mp3
        all_choices = self.hi_choices + self.bye_choices + self.init_greetings + [self.explain_sentence]
        for sentence in tqdm(all_choices, desc="Warmup cache with hi and bye phrases"):
            file_name = self._get_cache_file_name(sentence)
            if not os.path.exists(file_name):
                # Render the sentence to the specified file in mp3 format
                self.tts_provider.render_sentence(sentence=sentence, store_file_name=file_name, output_format='mp3')

    def _get_cache_file_name(self, sentence: str):
        # Create a short hash based on the sentence content
        hash_obj = hashlib.md5(sentence.encode('utf-8'))
        # Truncate the hash for a shorter filename if desired
        hash_str = hash_obj.hexdigest()[:8]
        return os.path.join("tts_cache/", f"{hash_str}.mp3")

    def _load_mp3_to_wav_bytesio(self, mp3_path: str) -> Tuple[int, io.BytesIO]:
        # Load the MP3 file into an AudioSegment
        audio_segment = AudioSegment.from_mp3(mp3_path)
        # Create a BytesIO buffer to hold WAV data
        wav_bytes = io.BytesIO()
        # Export the audio segment as WAV into the BytesIO buffer
        audio_segment.export(wav_bytes, format="wav")
        # Reset the buffer's position to the beginning
        wav_bytes.seek(0)
        # convert to ndarray
        data, sample_rate = sf.read(wav_bytes, dtype='float32')
        return sample_rate, data