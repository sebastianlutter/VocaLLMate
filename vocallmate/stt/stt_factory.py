import os

def SttFactory():
    provider_name=os.getenv('STT_PROVIDER', 'whisper')
    match provider_name:
        case 'whisper':
            from vocallmate.stt.stt_whisper_remote import SpeechToTextWhisperRemote
            p = SpeechToTextWhisperRemote()
        case 'speech-recognition':
            from vocallmate.stt.stt_speech_recognition_local import SpeechToTextSpeechRecognitionLocal
            p = SpeechToTextSpeechRecognitionLocal()
        case _:
            raise Exception(f"SttFactory: unknown provider name {provider_name}")
    print(f"SttFactory: start {provider_name} provider. {p.config_str()}")
    return p