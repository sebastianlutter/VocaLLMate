import time
import logging
import subprocess
from vocallmate.tts.tts_interface import TextToSpeechInterface
import pyttsx3


class TextToSpeechPyTtsx(TextToSpeechInterface):
    """
    Using espeak via pyttsx3. This fails to recognize the mbrola voices, so only the bad default voice works well
    """
    def __init__(self, voice_rate=150, voice='German'):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.engine = pyttsx3.init(debug=True, )  # object creation
        self.engine.setProperty('rate', voice_rate)  # setting up new voice rate
        self.engine.setProperty('voice', 'German')
        #self.engine.setProperty('voice', 'mb-de5')

    def speak_sentence(self, sentence: str):
        self.engine.say(sentence)
        self.engine.runAndWait()


class TextToSpeechEspeakCli(TextToSpeechInterface):
    """
    Alternative version of using espeak directly using CLI tools
    """
    def __init__(self, voice_rate=150, voice='mb-de2'):
        super().__init__()
        self.voice_rate = voice_rate
        self.voice = voice

    def speak_sentence(self, sentence: str):
        cmd = [
            'espeak',
            '-v', self.voice,
            '-s', str(self.voice_rate),
            sentence
        ]
        logging.debug(f"Command: {' '.join(cmd)}")
        # Use espeak via subprocess to speak the sentence
        # -v <voice> sets the voice; -s <speed> sets the speaking rate
        subprocess.run(cmd, check=True)
        time.sleep(0.5)

