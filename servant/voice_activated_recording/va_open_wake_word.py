import openwakeword
import wave
from openwakeword.model import Model
from servant.voice_activated_recording.va_interface import VoiceActivationInterface
from io import BytesIO
import time
from numpy import np

model_path = '/path/to/model'
inference_framework = 'tflite'

# Load pre-trained openwakeword models
if model_path != "":
    owwModel = Model(wakeword_models=[model_path], inference_framework=inference_framework)
else:
    owwModel = Model(inference_framework=inference_framework)

n_models = len(owwModel.models.keys())


class OpenWakewordActivated(VoiceActivationInterface):

    def __init__(self):
        super().__init__()
        self.wake_word = self.wakeword
        # Configurable delay before counting silence
        self.silence_lead_time = 2
        # One-time download of all pre-trained models (or only select models)
        openwakeword.utils.download_models()
        # Instantiate the model(s)
        self.model = Model(
            wakeword_models=["path/to/model.tflite"],  # can also leave this argument empty to load all of the included pre-trained models
            enable_speex_noise_suppression=True,
            vad_threshold=self.silence_threshold/100.0,
        )

    def listen_for_wake_word(self):
        # Generate output string header
        print("\n\n")
        print("#" * 100)
        print("Listening for wakewords...")
        print("#" * 100)
        print("\n" * (n_models * 3))
        while True:
            # Get audio
            audio = np.frombuffer(self.soundcard.get_record_stream().read(self.soundcard.frames_per_buffer), dtype=np.int16)
            # Feed to openWakeWord model
            prediction = owwModel.predict(audio)
            # Column titles
            n_spaces = 16
            output_string_header = """
                Model Name         | Score | Wakeword Status
                --------------------------------------
                """
            for mdl in owwModel.prediction_buffer.keys():
                # Add scores in formatted table
                scores = list(owwModel.prediction_buffer[mdl])
                curr_score = format(scores[-1], '.20f').replace("-", "")

                output_string_header += f"""{mdl}{" " * (n_spaces - len(mdl))}   | {curr_score[0:5]} | {"--" + " " * 20 if scores[-1] <= 0.5 else "Wakeword Detected!"}
                """
            # Print results table
            print("\033[F" * (4 * n_models + 1))
            print(output_string_header, "                             ", end='\r')
