from servant.tts.tts_interface import TextToSpeechInterface
import pyttsx3


class TextToSpeehPyTtsx(TextToSpeechInterface):

    def __init__(self):
        self.engine = pyttsx3.init()  # object creation
        """ RATE"""
        rate = self.engine.getProperty('rate')  # getting details of current speaking rate
        print(rate)  # printing current voice rate
        self.engine.setProperty('rate', 125)  # setting up new voice rate
        """VOLUME"""
        volume = self.engine.getProperty('volume')  # getting to know current volume level (min=0 and max=1)
        print(volume)  # printing current volume level
        self.engine.setProperty('volume', 1.0)  # setting up volume level  between 0 and 1
        """VOICE"""
        voices = self.engine.getProperty('voices')  # getting details of current voice
        # engine.setProperty('voice', voices[0].id)  #changing index, changes voices. o for male
        self.engine.setProperty('voice', voices[1].id)  # changing index, changes voices. 1 for female

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
        #self.engine.stop()


if __name__ == '__main__':
    tts = TextToSpeehPyTtsx()
    tts.speak("Das ist ein test. This is a test.")