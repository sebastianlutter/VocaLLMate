from threading import Thread

import torch
import warnings
import pyaudio
import numpy as np
from transformers import AutoProcessor, BarkModel

from servant.audio_device.soundcard_factory import SoundcardFactory
from servant.tts.tts_interface import TextToSpeechInterface

warnings.filterwarnings(
    "ignore",
    message="torch.nn.utils.weight_norm is deprecated in favor of torch.nn.utils.parametrizations.weight_norm."
)


class TextToSpeechTransformer(TextToSpeechInterface):
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initializes the TextToSpeechService class.

        Args:
            device (str, optional): The device to be used for the model, either "cuda" if a GPU is available or "cpu".
            Defaults to "cuda" if available, otherwise "cpu".
        """
        super().__init__()
        self.device = device
        self.processor = AutoProcessor.from_pretrained("suno/bark-small")
        self.model = BarkModel.from_pretrained("suno/bark-small")
        self.model.to(self.device)
        self.soundcard = SoundcardFactory()

    def speak_sentence(self, sentence: str):
        """
        Synthesizes the sentence and plays it back using pyaudio.
        """
        sample_rate, audio_array = self.synthesize(sentence)
        # create a thread to send audio to the soundcard
        return Thread(target=self.soundcard.play_audio, args=(sample_rate, audio_array))


    def synthesize(self, text: str, voice_preset: str = "v2/de_speaker_1"):
        """
        Synthesizes audio from the given text using the specified voice preset.

        Args:
            text (str): The input text to be synthesized.
            voice_preset (str, optional): The voice preset to be used for the synthesis. Defaults to "v2/de_speaker_1".

        Returns:
            tuple: A tuple containing the sample rate and the generated audio array.
        """
        inputs = self.processor(text, voice_preset=voice_preset, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            audio_array = self.model.generate(**inputs, pad_token_id=10000)

        # Convert to CPU numpy array
        audio_array = audio_array.cpu().numpy().squeeze()

        # Bark typically returns audio in float32 format, so it's already good for PyAudio
        sample_rate = self.model.generation_config.sample_rate
        return sample_rate, audio_array

if __name__ == '__main__':
    tts = TextToSpeechTransformer()
    tts.speak_sentence("Hello world")
