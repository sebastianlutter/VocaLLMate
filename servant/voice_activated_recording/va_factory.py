import os

def VoiceActivatedRecordingFactory():
    provider_name=os.getenv('WAKEWORD_PROVIDER', 'speech-recognition')
    match provider_name:
        case 'stt-provider-va':
            from servant.voice_activated_recording.va_stt_provider import SttProviderWakeWord
            p = SttProviderWakeWord()
        case 'picovoice':
            from servant.voice_activated_recording.va_picovoice import PorcupineWakeWord
            p = PorcupineWakeWord()
        case _:
            raise Exception(f"VoiceActivationFactory: unknown provider name {provider_name}")
    print(f"VoiceActivationFactory: start {provider_name} provider: {p.config_str()}")
    return p
