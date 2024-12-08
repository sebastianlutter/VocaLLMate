import os

def SttFactory():
    provider_name=os.getenv('STT_PROVIDER', 'whisper')
    match provider_name:
        case 'whisper':
            from servant.stt.stt_whisper_remote import SpeechToTextWhisperRemote
            p = SpeechToTextWhisperRemote()
            print(f"SttFactory: start whisper remote provider. {p.config_str()}")
            return p
        case _:
            raise Exception(f"SttFactory: unknown provider name {provider_name}")
