import os
import threading

# Thread lock for singleton initialization
_soundcard_lock = threading.Lock()
_soundcard_instance = None

def SoundcardFactory():
    global _soundcard_instance

    if _soundcard_instance is None:
        with _soundcard_lock:  # Ensure thread safety
            if _soundcard_instance is None:  # Double-check locking
                provider_name = os.getenv('AUDIO_PYTHON_BACKEND', 'pyaudio')
                match provider_name:
                    case 'pyaudio':
                        from servant.audio_device.soundcard_pyaudio import SoundCard
                    case _:
                        raise Exception(f"SoundcardFactory: unknown provider name {provider_name}")

                # Initialize the single instance
                _soundcard_instance = SoundCard()
                print(f"SoundcardFactory: start {provider_name} provider. {_soundcard_instance.config_str()}")

    return _soundcard_instance
