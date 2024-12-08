import os


def SoundcardFactory():
    provider_name=os.getenv('AUDIO_PYTHON_BACKEND', 'pyaudio')
    match provider_name:
        case 'pyaudio':
            from servant.audio_device.soundcard_pyaudio import SoundCard
        case 'pyalsaaudio':
            from servant.audio_device.soundcard_pyalsaaudio import SoundCard
        case _:
            raise Exception(f"SttFactory: unknown provider name {provider_name}")
    p = SoundCard()
    print(f"SoundcardFactory: start {provider_name} provider. {p.config_str()}")
    return p