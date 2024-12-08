# local-servant-llm
Toy project to make tests with LLMs, tts, stt and graph based processing. Goal is to build an application that get user input from microphone and answers with a spoken response.

The main idea is:
* run all components as docker-compose ensembles and access them via API (LLM, TTS, STT).
* use burr library to define application as a graph.

The application graph looks like this:
![Graph](./graph.png)


## Folders with -stack in their name
Each folder with `-stack` in their name contains a component that can be started using docker compose. For ease of 
use the script `stacks.sh` can be used to start and stop them.

```
# Show status
./stacks.sh
# Start stacks
./stacks.sh start
# Stop stacks
./stacks.sh stop
```
The script automatically checks if nvidia/cuda is available. If so the `docker-compose-cuda.yaml` files are used (NVIDIA container). Else the cpu stacks in `docker-compose.yaml` are used. 

To force the usage of cuda stacks you can also run:
```
./stacks.sh start
```

## The application

* First create a venv and install dependencies
```
python3 -mvenv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
* Create a `.env` config file, adjust as needed
```
cp _env .env
```

* Then run application
```
python3 main.py
```
## Configuration

The application uses ENV variables to configure all aspects of the application.
When running local use a `.env` file, else set them as host environment variables.

| variable                | default                                       | possible values                          |
|-------------------------|-----------------------------------------------|------------------------------------------|
| TTS_ENDPOINT            | http://127.0.0.1:8000/v1/audio/transcriptions | any http endpoint                        |
| TTS_PROVIDER            | pyttsx                                        | pyttsx, transformers                     |
| STT_PROVIDER            | whisper                                       | whisper                                  |
| STT_ENDPOINT            | local                                         | local                                    |
| WAKEWORD_PROVIDER       | speech-recognition                            | speech-recognition, open-wakeword        |
| WAKEWORD_THRESHOLD      | 250                                           | any positive integer                     |
| WAKEWORD                | computer                                      | any word or short phrase                 |
| AUDIO_PLAYBACK_DEVICE   | 0                                             | the device number, negative means "auto" |
| AUDIO_MICROPHONE_DEVICE | 0                                             | the device number, negative means "auto" |
| LLM_PROVIDER            | ollama                                        | ollama                                   |
| LLM_ENDPOINT            | http://127.0.0.1:11434                        | any http endpoint                        |
| LLM_PROVIDER_MODEL      | llama3.2:1b                                   | llama3.2:1b, llama3.2:3b                 |

