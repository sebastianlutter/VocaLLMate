import os

def VoiceActivationFactory():
    provider_name=os.getenv('WAKEWORD_PROVIDER')
    match provider_name:
        case 'pyaudio':
            from servant.voice_activation.voice_activation import VoiceActivatedRecorder
            p = VoiceActivatedRecorder()
            print(f"VoiceActivationFactory: start pyaudio provider. {p.config_str()}")
            return p
        case _:
            raise Exception(f"VoiceActivationFactory: unknown provider name {provider_name}")
