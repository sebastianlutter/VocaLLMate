import openai
from servant.audio_device.soundcard_factory import SoundcardFactory
from servant.tts.tts_interface import TextToSpeechInterface
from io import BytesIO
import soundfile as sf

class TextToSpeechOpenedaiSpeech(TextToSpeechInterface):
    """
    Using OpenAI's Text-to-Speech API to convert text to audio on the fly.
    Audio is played back immediately using PyAudio without saving to disk.
    """
    def __init__(self):
        super().__init__()
        self.client = openai.OpenAI(
            # Set environment variables for API configuration
            api_key="sk-111111111",
            base_url=self.tts_endpoint,
        )

    def speak_sentence(self, sentence: str):
        # Launch a thread to handle speech synthesis and playback
        # Generate speech using OpenAI's API
        response = self.client.audio.speech.create(
            model="tts-1",
            voice="thorsten-low",
            #voice="thorsten-medium",
            #voice="thorsten-medium-emo",
            response_format="wav",
            speed="1.0",
            input=sentence,
        )
        audio_stream = BytesIO(response.content)  # Use response.content to access binary audio data
        audio_stream.seek(0)  # Reset the buffer pointer to the start
        # Decode MP3 to WAV in-memory
        data, sample_rate = sf.read(audio_stream, dtype='float32')
        self.soundcard.play_audio(sample_rate, data)

    def render_sentence(self, sentence: str, store_file_name: str, output_format: str = 'mp3'):
        if output_format not in ["mp3", "wav"]:
            raise Exception("Only mp3 and wav are allowed as formats")
        # Generate speech using OpenAI's API
        response = self.client.audio.speech.create(
            model="tts-1",
            # voice="thorsten-low",
            voice="thorsten-medium",
            #voice="thorsten-medium-emo",
            response_format="mp3",
            speed="1.0",
            input=sentence,
        )
        audio_stream = BytesIO(response.content)
        # Save the audio_stream as an MP3 file
        with open(store_file_name, "wb") as f:
            f.write(audio_stream.getbuffer())

