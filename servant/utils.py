import json
import requests
from voice_activation.voice_activation import VoiceActivatedRecorder

record_request = VoiceActivatedRecorder()

def get_speech_input():
    # get recording from user
    audio_buffer = record_request.listen_for_wake_word()
    # transcribe the recording
    transcription = send_audio_to_service(audio_buffer)
    return transcription

def send_audio_to_service(audio_buffer):
    url = 'http://localhost:8000/v1/audio/transcriptions'
    # setting stream to true makes the json parse fail
    files = {'file': ('audio.wav', audio_buffer, 'audio/wav'), 'stream': (None, 'false')}
    # Send the POST request with the audio file
    response = requests.post(url, files=files)
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
