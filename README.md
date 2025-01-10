# local-servant-llm

Toy project to make tests with LLMs, tts, stt and graph based processing. Goal is to build an application that get user input from microphone and answers with a spoken response.

The main idea is:

* run all components as docker-compose ensembles and access them via API (LLM, TTS, STT).
* use burr library to define application as a graph.
* use german as the main language

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

* Then run application (default configuration is used then, see below)

  ```
  python3 main.py
  ```

  ## Configuration

The application uses ENV variables to configure all aspects of the application.
When running local use a `.env` file, else set them as host environment variables.

| variable                | default                                        | possible values                          |
| ----------------------- |------------------------------------------------|------------------------------------------|
| TTS_ENDPOINT            | http://127.0.0.1:8001/v1                       | any http endpoint                        |
| TTS_PROVIDER            | openedai                                       | openedai, pyttsx, transformers           |
| STT_PROVIDER            | whisper                                        | whisper, speech-recognition              |
| STT_ENDPOINT            | http://127.0.0.1:8000/v1/audio/transcriptions  | url if remote service has been chosen    |
| WAKEWORD_PROVIDER       | speech-recognition                             | speech-recognition, open-wakeword        |
| WAKEWORD_THRESHOLD      | 250                                            | any positive integer                     |
| WAKEWORD                | computer                                       | any word or short phrase                 |
| AUDIO_PLAYBACK_DEVICE   | -1                                             | the device number, negative means "auto" |
| AUDIO_MICROPHONE_DEVICE | -1                                             | the device number, negative means "auto" |
| AUDIO_PYTHON_BACKEND    | pyaudio                                        | pyaudio, pyalsaaudio                     |
| LLM_PROVIDER            | ollama                                         | ollama                                   |
| LLM_ENDPOINT            | http://127.0.0.1:11434                         | any http endpoint                        |
| LLM_PROVIDER_MODEL      | llama3.2:1b                                    | llama3.2:1b, llama3.2:3b                 |


* Create a `.env` config file from the given example and adjust as needed

  ```
  cp _env .env
  ```

If no `.env` is found and no environment variables are set then the defaults are used. You need to provide only the
settings you want to overwrite.

## PyTTSX

The pyttsx package can use multiple backends from the host linux system for text-to-speech synthesis. Consider
to install the following:

```
apt install espeak ffmpeg libespeak1
# german voices that replace the mechanical one that espeak ships with
apt install mbrola mbrola-de1 mbrola-de2 mbrola-de3 mbrola-de4 mbrola-de5 mbrola-de6 mbrola-de7 mbrola-de8
```

You can list the available voices on your host system with:

```
import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')
for voice in voices:
    print(f"ID: {voice.id}")
    print(f"Name: {voice.name}")
    print(f"Languages: {voice.languages}")
    print("------")
```

## speech-recognition backend vosk

The SpeechRecognition package supports multiple online and offline backends. This project uses the VOSK offline
backend. First a model needs to be downloaded from https://alphacephei.com/vosk/models

* For a slim model use https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
* For a good balance use https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip
* Best quality use https://alphacephei.com/vosk/models/vosk-model-de-tuda-0.6-900k.zip

Extract the ZIP in project root and rename the extracted filename to `model/` so VOSK is able to find it.

```
unzip vosk-model-de-0.21.zip
mv vosk-model-de-0.21 model
```

## Pyaudio und portaudio

Pyaudio is used to access the soundcard. To install the python dependency you
may need to install portaudio development files into your host system:
```
apt install portaudio19-dev
```

## PyDub

PyDub uses ffmpeg binaries on the host system, make sure ffmpeg is installed in the host system
```
apt install ffmpeg
```

## Docker environment with PyTorch 2.5.1 GPU support

There is a development docker to run the application in a pytorch enabled environment with GPU support. The `Dockerfile`
and `runDevDocker.sh` script can be used for this purpose.

Build and run the dev docker and mount the project into the workdir:

```
./runDevDocker.sh
```

# README - Usage of the optional_checks.yaml File

This project supports additional checks ("optional checks") defined in an **optional_checks.yaml** file. If this file is present, all listed services will be checked automatically. If it is not present, no optional checks will be performed.

## YAML File Structure

The **optional_checks.yaml** can contain multiple entries (checks). Each entry describes one service to be checked. Typically, the following fields are used per entry:

- **name**: The name of the service (freely chosen, e.g., "My SSH Server").
- **type**: The type of service. Currently, the following types are supported:
  - `ssh` – Performs an SSH check (connection + simple command).
  - `http` – Performs an HTTP check (e.g., a GET request to a URL).
- **host** (only for `ssh`): Hostname or IP address of the target system.
- **user** (only for `ssh`): Username for the SSH connection.
- **endpoint** (only for `http`): Full URL to be requested (GET or POST).
- **wake_if_down** (optional): A MAC address (e.g., `00:11:22:33:44:55`) to attempt a Wake-on-LAN if the initial check fails. The check will then be retried once.

> **Note**: If `wake_if_down` is specified and the first check (SSH or HTTP) fails, the code sends a Wake-on-LAN packet to the specified MAC address. It then waits up to 30 seconds (in 5-second intervals) before performing a second check. If this second check also fails, the service is ultimately marked as unavailable.

#### SSH 
Make sure all `ssh` hosts and user have access using the users ssh key as auth.
On the machine running this application make sure a SSH keypair exists (use `ssh-keygen -trsa` if not).
Then make sure your ssh key is in the `authorized_keys` of the target machine:
```
ssh-copy-id USER@IP
```

#### Example optional_checks.yaml

```yaml
optional_checks:
  - name: "Example-SSH"
    type: "ssh"
    host: "192.168.1.10"
    user: "pi"
    wake_if_down: "AA:BB:CC:DD:EE:FF"

  - name: "Example-HTTP"
    type: "http"
    endpoint: "https://example.com/health"
```

In this example, there is one SSH service and one HTTP service. For the SSH check, if it fails, a Wake-on-LAN packet is sent to the specified MAC address `AA:BB:CC:DD:EE:FF`, and the check is retried once.

#### Behavior if the File Is Missing

If the **optional_checks.yaml** file is not present or contains no entries, no additional services are checked. The application will then only test the mandatory services (STT, TTS, and LLM).

## Links / unfinished stuff

* https://github.com/matatonic/openedai-speech
* https://github.com/DigitalPhonetics/IMS-Toucan
* https://github.com/thorstenMueller/Thorsten-Voice
