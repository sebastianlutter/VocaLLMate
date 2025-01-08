import os
import json
import time
import vosk
import asyncio
import logging
from vocallmate.stt.stt_interface import SpeechToTextInterface


class SpeechToTextSpeechRecognitionLocal(SpeechToTextInterface):
    """
    A local STT class that mimics the streaming functionality of SpeechToTextWhisperRemote.

    Instead of sending audio to a remote WebSocket server, it uses the Vosk engine locally.
    It supports partial recognition by yielding partial transcripts on each chunk.
    Automatically ends transcription if no speech is detected for 3 seconds.
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Prepare your Vosk model. Adjust path or use environment variable VOSK_MODEL_PATH if desired.
        model_path = os.getenv("VOSK_MODEL_PATH", "./model")
        if not os.path.isdir(model_path):
            raise RuntimeError(f"Vosk model folder not found at: {model_path}")

        self.model = vosk.Model(model_path)
        # We create one KaldiRecognizer for the standard 16k single-channel audio
        # If you need more advanced usage (e.g., multi-channel), adjust here.
        self.sample_rate = 16000
        self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        self.NO_SPEECH_TIMEOUT = 3.0  # seconds of silence before ending

    async def transcribe_stream(
            self,
            audio_stream: asyncio.coroutines,  # i.e., AsyncGenerator[bytes, None]
            websocket_on_close,
            websocket_on_open
    ):
        """
        Asynchronously consumes raw 16-bit PCM audio chunks from `audio_stream`,
        processes them locally via the Vosk engine, and yields partial or final transcripts.

        This mimics the signature and behavior from SpeechToTextWhisperRemote:
         - `websocket_on_open()` is called right before we start reading audio.
         - `websocket_on_close()` is called after we finish or hit an error.
         - Yields incremental text output (partial results).
         - Terminates if there's no recognized speech for self.NO_SPEECH_TIMEOUT seconds.
        """

        # We call the "on_open" callback just for consistency with the remote class
        websocket_on_open()
        self.logger.debug("Local streaming STT started.")

        old_full_text = ""       # Accumulate final recognized text
        old_partial_text = ""    # Track partial text for incremental updates
        last_speech_time = time.time()  # When we last got *any* recognized text

        try:
            while True:
                # Pull the next chunk from the audio stream
                try:
                    chunk = await audio_stream.__anext__()
                except StopAsyncIteration:
                    # The audio stream ended
                    break

                # Feed the chunk to Vosk's recognizer
                is_final = self.recognizer.AcceptWaveform(chunk)

                if is_final:
                    # Final result for this chunk
                    res = json.loads(self.recognizer.Result())
                    final_text = res.get("text", "")

                    # Determine the newly recognized text portion
                    diff = final_text[len(old_full_text):]
                    old_full_text = final_text

                    if diff.strip():
                        yield diff
                        # We heard actual speech -> reset silence timer
                        last_speech_time = time.time()
                    # else: it's an empty final => continue

                else:
                    # We only got a partial (interim) result
                    partial_res = json.loads(self.recognizer.PartialResult())
                    partial_text = partial_res.get("partial", "")

                    # Identify the newly recognized partial portion
                    diff = partial_text[len(old_partial_text):]
                    old_partial_text = partial_text

                    if diff.strip():
                        yield diff
                        # We heard actual speech -> reset silence timer
                        last_speech_time = time.time()

                # Check if we've been silent too long
                if (time.time() - last_speech_time) > self.NO_SPEECH_TIMEOUT:
                    self.logger.debug("No speech detected for 3 seconds, ending transcription.")
                    break

            # Once the stream is fully consumed or we've timed out, get leftover final
            final_res = json.loads(self.recognizer.FinalResult())
            final_text = final_res.get("text", "")
            diff = final_text[len(old_full_text):]
            if diff.strip():
                yield diff

        except BaseException as e:
            self.logger.error(f"exception: {type(e)} {e}")
        finally:
            self.logger.debug("closing local STT.")
            # For consistency, call the "websocket_on_close" callback
            websocket_on_close()
