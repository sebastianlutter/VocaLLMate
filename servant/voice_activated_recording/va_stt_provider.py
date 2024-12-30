import os
import asyncio
import webrtcvad

from servant.voice_activated_recording.va_interface import VoiceActivationInterface
from servant.audio_device.soundcard_factory import SoundcardFactory
from servant.stt.stt_whisper_remote import SpeechToTextWhisperRemote


class SttProviderWakeWord(VoiceActivationInterface):
    """
    A wakeword detection class that uses:
      1) WebRTC VAD to wait for any speech.
      2) Once speech is detected, uses the SpeechToTextWhisperRemote streaming
         to capture and transcribe until the remote service closes or
         we find the wakeword in the transcript. If the wakeword is found,
         we return immediately.
      3) If the STT ends without detecting the wakeword, we go back to VAD listening.
    """

    def __init__(self):
        super().__init__()
        # Remote whisper-based STT object
        self.stt = SpeechToTextWhisperRemote()

        # Initialize a very aggressive VAD mode (3). Adjust if too sensitive / not sensitive enough.
        self.vad = webrtcvad.Vad(mode=3)

        # Typically, your soundcard should produce 16-bit, 1-channel, 16kHz audio
        # to match the VAD's default expectations.
        # We'll chunk up frames into 20ms slices for VAD checks:
        self.vad_frame_ms = 20

    async def listen_for_wake_word(self):
        """
        Continuously:
          - Use VAD to detect if someone starts speaking.
          - Then run the remote Whisper streaming to see if the wakeword is spoken.
          - If the STT ends without detecting the wakeword, go back to VAD listening.
        """
        print(f"Listening for wake word: {self.wakeword}")

        while True:
            # 1) Wait until there's any speech (via VAD)
            print("WhisperRemoteWakeWord.listen_for_wake_word: waiting for speech via VAD...")
            speech_detected = await self._wait_for_speech()
            if not speech_detected:
                # If _wait_for_speech somehow returned False, just continue
                continue

            print("Speech detected, starting remote transcription...")

            # 2) Now open a fresh record stream for STT
            audio_stream = self.soundcard.get_record_stream()

            def on_ws_open():
                print("WhisperRemoteWakeWord.listen_for_wake_word: WebSocket opened.")

            def on_ws_close():
                print("WhisperRemoteWakeWord.listen_for_wake_word: WebSocket closed.")

            try:
                # 3) Stream to Whisper and look for the wake word
                async for partial_text in self.stt.transcribe_stream(
                    audio_stream=audio_stream,
                    websocket_on_close=on_ws_close,
                    websocket_on_open=on_ws_open
                ):
                    # Check if partial transcript includes wakeword
                    if self.wakeword.lower() in partial_text.lower():
                        print(f"Wake word '{self.wakeword}' detected!")
                        return

                # If the transcription generator ended without detecting wakeword
                print("Remote STT ended. Going back to VAD listening...")

            except asyncio.CancelledError:
                print("WhisperRemoteWakeWord.listen_for_wake_word: Cancelled.")
                return
            except Exception as e:
                print(f"WhisperRemoteWakeWord.listen_for_wake_word: error in STT: {e}")
                # Return to VAD loop
                await asyncio.sleep(1.0)

    async def _wait_for_speech(self) -> bool:
        """
        Continuously reads raw audio from the soundcard in small chunks.
        Checks each chunk for speech using WebRTC VAD.
        Returns True as soon as we detect speech.
        If the audio stream ends for some reason, we return False.
        """
        audio_stream = self.soundcard.get_record_stream()
        try:
            async for chunk in audio_stream:
                if self._chunk_has_speech(chunk):
                    return True
        except Exception as e:
            print(f"_wait_for_speech: Audio stream ended or error: {e}")
        return False

    def _chunk_has_speech(self, chunk: bytes) -> bool:
        """
        Break `chunk` into 20ms frames and check if any frame has speech
        according to WebRTC VAD.
        - chunk is 16-bit, mono, 16kHz PCM => 1 sample = 2 bytes, 1 second = 32000 bytes
        - 20ms = 0.02s => 320 samples => 640 bytes
        """
        frame_size = int(self.soundcard.sample_rate * (self.vad_frame_ms / 1000.0))  # in samples
        bytes_per_frame = frame_size * 2  # 2 bytes per sample for 16-bit
        idx = 0
        while idx + bytes_per_frame <= len(chunk):
            frame = chunk[idx: idx + bytes_per_frame]
            # webrtcvad expects 16-bit little-endian, 1ch, 16k sample rate
            if self.vad.is_speech(frame, self.soundcard.sample_rate):
                return True
            idx += bytes_per_frame
        return False
