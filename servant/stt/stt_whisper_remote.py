import json
import time
from typing import Generator, Callable, AsyncGenerator
import websocket
import requests
import threading
import asyncio
import io
import wave
from websocket import WebSocket
from queue import Queue

from servant.stt.stt_interface import SpeechToTextInterface
from websocket import WebSocket, WebSocketApp, ABNF

# see
dataset_bias = [
    "Untertitelung aufgrund der Amara.org-Community"
    "Untertitel im Auftrag des ZDF für funk, 2017",
    "Untertitel von Stephanie Geiges",
    "Untertitel der Amara.org-Community",
    "Untertitel  der  Amara .org -Community",
    "Untertitel im Auftrag des ZDF, 2017",
    "Untertitel im Auftrag des ZDF, 2020",
    "Untertitel im Auftrag des ZDF, 2018",
    "Untertitel im Auftrag des ZDF, 2021",
    "Untertitelung im Auftrag des ZDF, 2021",
    "Copyright WDR 2021",
    "Copyright WDR 2020",
    "Copyright WDR 2019",
    "SWR 2021",
    "SWR 2020",
]


class SpeechToTextWhisperRemote(SpeechToTextInterface):

    def __init__(self):
        super().__init__()
        self.url= self.stt_endpoint
        # use the http endpoint for websocket
        self.ws_url = self.stt_endpoint.replace('http://','ws://')
        websocket.enableTrace(False)

    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None], websocket_on_close: Callable[[], None], websocket_on_open: Callable[[], None]) -> AsyncGenerator[str, None]:
        print("stt_whisper_remote.transcribe_stream: streaming data to whisper server . . .")
        queue = Queue()  # Back channel for transcription results
        # A callback function for receiving messages from the WebSocket
        def on_message(wsc: WebSocket, message: str):
            print(f"ON MESSAGE: {message}")
            try:
                # remove unwanted response, see
                # https://github.com/openai/whisper/discussions/1536
                for txt in dataset_bias:
                    if txt in message:
                        message = message.replace(txt,'')
                result = json.loads(message)
                if 'text' in result and result['text'].strip():
                    print("stt_whisper_remote.transcribe_stream: got: "+ result['text'])
                    queue.put(result['text'])  # Push the transcription result into the queue
            except json.JSONDecodeError:
                print(f"stt_whisper_remote.transcribe_stream: got non json: {message}")
                pass  # Ignore non-JSON messages
        # A synchronous callback for handling WebSocket connection establishment
        thread_stop_event =  threading.Event()
        # Collect the WAV data from the stream into a BytesIO buffer
        def on_open(wsc2: WebSocket):
            print(f"stt_whisper_remote.transcribe_stream: Successfully connected websocket {self.ws_url}")
            # call external callback
            websocket_on_open()
            def send_audio_chunks():
                try:
                    start_time_sending = time.time()
                    wav_buffer = io.BytesIO()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    async def send_chunks():
                        with wave.open(f=wav_buffer, mode='wb') as wav_file:
                            wav_file.setnchannels(1)  # Mono audio
                            wav_file.setsampwidth(2)  # 16-bit depth (2 bytes)
                            wav_file.setframerate(16000)
                            wav_file.setcomptype('NONE', 'not compressed')  # PCM format (no compression)
                            #print(wav_file.getparams())
                            async for wav_chunk in audio_stream:
                                if thread_stop_event.is_set():  # Check if the stop event is set
                                    print("stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks.send_chunks: Stop signal received, exiting send_chunks.")
                                    loop.stop()
                                    break
                                wav_file.writeframes(wav_chunk)
                                # websocket needs raw PCM (pcm_s16le) encoded bytes
                                # Only transcription of a single channel, 16000 sample rate, raw, 16-bit little-endian
                                # audio is supported.
                                wsc2.send(wav_chunk, opcode=ABNF.OPCODE_BINARY)
                    loop.run_until_complete(send_chunks())
                except KeyboardInterrupt:
                    # stopped by the user
                    websocket_on_close()
                    thread_stop_event.set()
                except BaseException as e:
                    print(f"stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks: Error in send_audio_chunks: {e}")
                    websocket_on_close()
                    thread_stop_event.set()
                finally:
                    print(f"stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks: Sending stuff to websocket for {time.time()-start_time_sending} seconds")
                    # Save the WAV buffer to a file
                    outfile = f'recoring_{time.strftime("%y%m%d-%H%M")}.wav'
                    print(f"stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks: Storing WAV: {outfile}")
                    with open(outfile, "wb") as f:
                        f.write(wav_buffer.getvalue())
                    print("stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks: Cleaning up thread resources.")
                    if wsc2:
                        print("stt_whisper_remote.transcribe_stream.on_open.send_audio_chunks: Close websocket")
                        wsc2.close()  # Close the WebSocket connection
                    if loop:
                        asyncio.
                        if loop.is_running():
                            loop.stop()
                        if not loop.is_closed():
                            loop.close()
                    thread_stop_event.set()
            # Start the thread to run async
            threading.Thread(target=send_audio_chunks, daemon=True).start()
        def on_error(ws, code):
            print(f"stt_whisper_remote.transcribe_stream.on_error: WebSocket error: {code}")
            websocket_on_close()
            thread_stop_event.set()
        def on_close(ws: WebSocket, i1, i2):
            print(f"stt_whisper_remote.transcribe_stream.on_error: WebSocket closed: {i1}, {i2}")
            queue.put(None)
            websocket_on_close()
            thread_stop_event.set()
        try:
            print(f"stt_whisper_remote.transcribe_stream: Starting websocket connection to {self.ws_url}")
            ws = WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            # Run the WebSocket in a separate thread to prevent blocking
            ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
            ws_thread.start()
            # Yield transcription results from the queue
            old_full_text = ''
            while not thread_stop_event.is_set():
                t = queue.get()
                if t is None:
                    break
                #print(f"websocket stream: {t}")
                t_diff = t[len(old_full_text):]
                # update the text
                old_full_text = t
                yield t_diff
            print(f"stt_whisper_remote.transcribe_stream: Transcription queue closed")
        except BaseException as e:
            print(f"stt_whisper_remote.transcribe_stream.BaseException: type={type(e)}, e={e}")
            thread_stop_event.set()
            if ws:
                ws.close()  # Gracefully close the WebSocket
            if ws_thread and ws_thread.is_alive():
                ws_thread.join(timeout=5)  # Ensure the thread has stopped
        finally:
            print(f"stt_whisper_remote.transcribe_stream: Cleanup completed")