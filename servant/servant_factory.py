from servant.stt.stt_factory import SttFactory
from servant.tts.tts_factory import TtsFactory
from servant.llm.llm_factory import LmmFactory
from servant.voice_activated_recording.va_factory import VoiceActivatedRecordingFactory

class ServantFactory:

    def __init__(self):
        self.stt_provider = SttFactory()
        self.tts_provider = TtsFactory()
        self.llm_provider = LmmFactory()
        self.va_provider = VoiceActivatedRecordingFactory()
