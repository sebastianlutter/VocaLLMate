from vocallmate.human_speech_agent import HumanSpeechAgent
from vocallmate.stt.stt_factory import SttFactory
from vocallmate.tts.tts_factory import TtsFactory
from vocallmate.llm.llm_factory import LlmFactory
from vocallmate.voice_activated_recording.va_factory import VoiceActivatedRecordingFactory

class ServantFactory:

    def __init__(self):
        self.stt_provider = SttFactory()
        self.tts_provider = TtsFactory()
        self.llm_provider = LlmFactory()
        self.va_provider = VoiceActivatedRecordingFactory()
        self.human_speech_agent = HumanSpeechAgent()

