from servant.tts.tts_interface import TextToSpeechInterface
import pyttsx3
import time


class TextToSpeechPyTtsx(TextToSpeechInterface):

    def __init__(self, voice_rate=150, voice='German'):
        super().__init__()
        self.engine = pyttsx3.init()  # object creation
        self.engine.setProperty('rate', voice_rate)  # setting up new voice rate
        #self.engine.setProperty('volume', 1.0)  # setting up volume level  between 0 and 1
        self.engine.setProperty('voice', 'German')

    def speak_sentence(self, sentence: str):
        self.engine.say(sentence)
        self.engine.runAndWait()

    def speak_loop(self):
        while True:
            sentence = self.queue.get()
            #print(f"Got sentence: {sentence}")
            self.engine.say(sentence)
            self.engine.runAndWait()
            # wait to have a small gap after each sentence
            time.sleep(1.2)

    def show_voices(self):
        engine = pyttsx3.init()
        for voice in engine.getProperty('voices'):
            print(f"{voice.id}\t{voice.languages}\t{voice.gender}")

if __name__ == '__main__':
    tts = TextToSpeechPyTtsx()
    tts.show_voices()
    tts.speak("Das ist ein test. This is a test.")