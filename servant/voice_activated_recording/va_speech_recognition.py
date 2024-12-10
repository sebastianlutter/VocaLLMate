import speech_recognition as sr
import json
from servant.voice_activated_recording.va_interface import VoiceActivationInterface
import io
import wave

class SpeechRecognitionActivated(VoiceActivationInterface):

    def __init__(self):
        super().__init__()
        self.wake_word = self.wakeword
        self.recognizer = sr.Recognizer()
        self.init()

    def init(self):
        print("Loading the voice activation model . . .")
        # Create an in-memory WAV file with a short period of silence
        silence_duration_seconds = 0.5
        sample_rate = 16000
        num_samples = int(sample_rate * silence_duration_seconds)
        num_channels = 1
        sample_width = 2  # 16-bit
        # Create silent audio bytes (all zeros)
        silent_frames = b"\x00" * (num_samples * num_channels * sample_width)
        # Write the silent WAV to an in-memory buffer
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(silent_frames)
        # Seek back to the start so AudioFile can read it
        wav_buffer.seek(0)
        # Use sr.AudioFile to convert into AudioData
        with sr.AudioFile(wav_buffer) as source:
            silent_audio = self.recognizer.record(source)
        # Now we have AudioData, we can call recognize_vosk
        try:
            # This forces the Vosk model to load
            self.recognizer.recognize_vosk(silent_audio, language='de')
        except sr.UnknownValueError:
            pass  # No actual words from silence expected

    def listen_for_wake_word(self):
        with sr.Microphone(device_index=self.soundcard.audio_microphone_device) as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("Listening for wake word...")
            transcript = ''
            while True:
                audio = self.recognizer.listen(source)
                try:
                    transcript = self.recognizer.recognize_vosk(audio, 'de').lower()
                    transcript = json.loads(transcript)['text']
                    print(f"SpeechRecognition: Got {transcript}")
                    if self.wake_word in transcript:
                        print(f"Wake word '{self.wake_word}' detected. Starting recording...")
                        return self.start_recording()
                except sr.UnknownValueError as e:
                    print(f"Could not understand audio: {transcript}")
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")

