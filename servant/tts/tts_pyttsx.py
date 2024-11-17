from servant.tts.tts_interface import TextToSpeechInterface
import pyttsx3


class TextToSpeechPyTtsx(TextToSpeechInterface):

    def __init__(self, voice_rate=125):
        self.engine = pyttsx3.init()  # object creation
        self.engine.setProperty('rate', voice_rate)  # setting up new voice rate
        #self.engine.setProperty('volume', 1.0)  # setting up volume level  between 0 and 1
        voices = self.engine.getProperty('voices')  # getting details of current voice
        self.engine.setProperty('voice', voices[1].id)  # changing index, changes voices. 1 for female

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
        #self.engine.stop()


if __name__ == '__main__':
    tts = TextToSpeechPyTtsx()
    tts.speak("Das ist ein test. This is a test.")