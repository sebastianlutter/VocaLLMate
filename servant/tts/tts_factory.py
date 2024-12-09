import os

def TtsFactory():
    provider_name=os.getenv('TTS_PROVIDER', 'pyttsx')
    match provider_name:
        case 'pyttsx':
            from servant.tts.tts_pyttsx import TextToSpeechPyTtsx, TextToSpeechEspeakCli
            #p = TextToSpeechPyTtsx()
            p = TextToSpeechEspeakCli()
            print(f"TtsFactory: start pyttsx provider. {p.config_str()}")
            return p
        case 'transformers':
            from servant.tts.tts_transformer import TextToSpeechTransformer
            p = TextToSpeechTransformer()
            print(f"TtsFactory: start transformers provider. {p.config_str()}")
            return p
        case _:
            raise Exception(f"TtsFactory: unknown provider name {provider_name}")
