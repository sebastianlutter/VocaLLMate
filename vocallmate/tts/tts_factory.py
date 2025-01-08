import os

def TtsFactory():
    provider_name=os.getenv('TTS_PROVIDER', 'pyttsx')
    match provider_name:
        case 'openedai':
            from vocallmate.tts.tts_openedai_speech import TextToSpeechOpenedaiSpeech
            p = TextToSpeechOpenedaiSpeech()
        case 'pyttsx':
            from vocallmate.tts.tts_pyttsx import TextToSpeechPyTtsx, TextToSpeechEspeakCli
            #p = TextToSpeechPyTtsx()
            p = TextToSpeechEspeakCli()
        case _:
            raise Exception(f"TtsFactory: unknown provider name {provider_name}")
    print(f"TtsFactory: start {provider_name} provider. {p.config_str()}")
    return p