import json
from typing import Generator, Callable, AsyncGenerator
import websocket
import requests
import threading
import asyncio
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
        print("transcribe_stream")
        queue = Queue()  # Back channel for transcription results
        # A callback function for receiving messages from the WebSocket
        def on_message(wsc: WebSocket, message: str):
            try:
                # remove unwanted response, see
                # https://github.com/openai/whisper/discussions/1536
                for txt in dataset_bias:
                    if txt in message:
                        message = message.replace(txt,'')
                result = json.loads(message)
                if 'text' in result and result['text'].strip():
                    queue.put(result['text'])  # Push the transcription result into the queue
            except json.JSONDecodeError:
                pass  # Ignore non-JSON messages
        # A synchronous callback for handling WebSocket connection establishment
        stop_event =  threading.Event()
        def on_open(wsc2: WebSocket):
            print(f"Successfully connected websocket {self.ws_url}")
            # call external callback
            websocket_on_open()

            def send_audio_chunks():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    async def send_chunks():
                        async for wav_chunk in audio_stream:
                            if stop_event.is_set():  # Check if the stop event is set
                                print("Stop signal received, exiting send_chunks.")
                                loop.stop()
                                break
                            wsc2.send(wav_chunk, opcode=ABNF.OPCODE_BINARY)
                    loop.run_until_complete(send_chunks())
                except BaseException as e:
                    print(f"Error in send_audio_chunks: {e}")
                    websocket_on_close()
                    stop_event.set()
                finally:
                    print("Cleaning up thread resources.")
                    wsc2.close()  # Close the WebSocket connection
                    loop.stop()
                    loop.close()
            # Start the thread to run async
            threading.Thread(target=send_audio_chunks, daemon=True).start()
        def on_error(ws, code):
            print(f"WebSocket on_error: {code}")
            websocket_on_close()
            stop_event.set()
        def on_close(ws: WebSocket, i1, i2):
            print(f"WebSocket on_close: {i1}, {i2}")
            queue.put(None)
            websocket_on_close()
            stop_event.set()
        try:
            print(f"Starting websocket connection to {self.ws_url}")
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
            while not stop_event.is_set():
                t = queue.get()
                if t is None:
                    break
                #print(f"websocket stream: {t}")
                t_diff = t[len(old_full_text):]
                # update the text
                old_full_text = t
                yield t_diff
            print("websocket stream closed: Closing queue")
        except BaseException as e:
            print(f"type={type(e)}")
            print(f"WebSocket stream ended. Got {e}")
            stop_event.set()
            if ws:
                ws.close()  # Gracefully close the WebSocket
            if ws_thread.is_alive():
                ws_thread.join(timeout=5)  # Ensure the thread has stopped
        finally:
            print("Cleanup completed")