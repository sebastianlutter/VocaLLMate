import json
import requests
from servant.stt.stt_interface import SpeechToTextInterface


class SpeechToTextWhisperRemote(SpeechToTextInterface):

    def __init__(self):
        super().__init__()
        self.url= self.stt_endpoint

    def transcribe(self, audio_buffer):
        # setting stream to true makes the json parse fail
        files = {'file': ('audio.wav', audio_buffer, 'audio/wav'), 'stream': (None, 'false')}
        # Send the POST request with the audio file
        response = requests.post(self.url, files=files)
        # Check the response status
        if response.status_code != 200:
            print(f"Error with request, Status Code: {response.status_code}")
            return None  # Or handle error as needed
        # Try to parse the JSON from the response
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            print("Failed to decode JSON from response")
            print("Response was:", response.text)
            return None
        # Extract the 'text' field from the JSON data
        if 'text' in data:
            return data['text']
        else:
            print("No 'text' field found in the JSON response")
            return None