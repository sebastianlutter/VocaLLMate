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

# README - Usage of the optional_actions.yaml File

This project supports additional checks ("optional checks") defined in an **optional_actions.yaml** file. If this file is present, all listed services will be checked automatically. If it is not present, no optional checks will be performed.

## YAML File Structure

The **optional_actions.yaml** can contain multiple entries (checks). Each entry describes one service to be checked. Typically, the following fields are used per entry:

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

#### Example optional_actions.yaml

This chapter explains how to configure **servers (targets)** and their **actions** (as well as high-level **functions**) within a YAML file. The YAML is used both by the `SystemStatus` class for checks (HTTP/SSH + optional Wake-on-LAN) and by an orchestrator class (like `ActionsOrchestrator`) for executing defined actions on each server.

Below is a reference sample of the **optional_actions.yaml** structure:

```yaml
optional_services:
  - name: "steamdeck"
    type: "ssh"
    host: "192.168.1.10"
    user: "deck"
    wake_if_down: "AA:BB:CC:DD:EE:FF"
    actions:
      - name: "start_game"
        description: "Starts a game on the Steamdeck"
        parameters:
          - name: "game_path"
            type: "str"
            description: "Absolute path to the game’s executable or launch script."
          - name: "additional_option"
            type: "int"
            description: "Optional numeric parameter (range 1-10)."
        check:
          method: "ssh"
          command: "ps aux | grep my_game"
        init:
          method: "ssh"
          command: "mkdir -p /home/deck/game_temp"
        run:
          method: "ssh"
          command: "cd /home/deck/game_dir && ./start_game.sh"

      - name: "pre_setup"
        description: "Prepares the Steamdeck environment"
        parameters: []
        check:
          method: "ssh"
          command: "test -d /home/deck"
        init:
          method: "ssh"
          command: "echo 'Nothing to init here'"
        run:
          method: "ssh"
          command: "sudo systemctl restart some_service"

  - name: "raspberry"
    type: "ssh"
    host: "192.168.1.20"
    user: "pi"
    actions:
      - name: "update_system"
        description: "Updates and upgrades the system packages"
        parameters:
          - name: "update_channel"
            type: "str"
            description: "Which update channel to use (e.g. 'stable', 'beta', or 'dev')."
        check:
          method: "ssh"
          command: "test -f /usr/bin/apt-get"
        init:
          method: "ssh"
          command: "sudo apt-get update"
        run:
          method: "ssh"
          command: "sudo apt-get upgrade -y"

  - name: "external-api"
    type: "http"
    endpoint: "https://api.example.com/health"
    actions:
      - name: "trigger_task"
        description: "Triggers a background task on the external API"
        parameters:
          - name: "task_id"
            type: "str"
            description: "Unique identifier for the task to be triggered."
          - name: "priority"
            type: "int"
            description: "Priority level of the task (1 = highest, 5 = default, 10 = lowest)."
        check:
          method: "http"
          endpoint: "https://api.example.com/can-trigger-task"
        init:
          method: "http"
          endpoint: "https://api.example.com/prepare"
        run:
          method: "http"
          endpoint: "https://api.example.com/trigger"

      - name: "check_auth"
        description: "Verifies that the user is authenticated for the external API"
        parameters: []
        check:
          method: "http"
          endpoint: "https://api.example.com/is-authenticated"
        init:
          method: "http"
          endpoint: "https://api.example.com/request-auth"
        run:
          method: "http"
          endpoint: "https://api.example.com/complete-auth"

functions:
  - name: "update_all_and_start_game"
    description: "Updates the Raspberry Pi and then starts a game on the Steamdeck."
    steps:
      - server: "raspberry"
        action: "update_system"
        parameters:
          update_channel: "stable"
      - server: "steamdeck"
        action: "pre_setup"
      - server: "steamdeck"
        action: "start_game"
        # If parameters are not defined, they will be asked from the user at runtime
        # parameters:
        #   game_path: "/home/deck/my_game.sh"
        #   additional_option: 2
```

---

## Overview

- **optional_services**: Top-level array where each entry represents a _server_ or _target_ that can be checked or used for actions.
- **functions**: Top-level array for _high-level sequences_ of actions (chaining multiple steps across one or more servers).

### 1. Server (Target) Entries

Each item under `optional_services` describes one server or external service. Common fields include:

1. **name** (string): A unique identifier for this server/target.  
2. **type** (string): The connection type, either `ssh` or `http`.  
3. **host** (string, optional): Required if `type` is `ssh`. Hostname or IP for SSH connection.  
4. **user** (string, optional): Required if `type` is `ssh`. The username for the SSH session.  
5. **endpoint** (string, optional): Required if `type` is `http`. The base endpoint or health-check URL.  
6. **wake_if_down** (string, optional): A MAC address used for Wake-on-LAN if the server fails the initial check (e.g., `"AA:BB:CC:DD:EE:FF"`).  
7. **actions** (array): A list of actionable items (commands, scripts, or HTTP calls) that can be performed on this server.

#### Example Server Definition

```yaml
- name: "steamdeck"
  type: "ssh"
  host: "192.168.1.10"
  user: "deck"
  wake_if_down: "AA:BB:CC:DD:EE:FF"
  actions: [...]
```

---

### 2. Actions

Each server can define one or more **actions**, each describing a set of instructions or commands to be performed. Fields inside each action:

- **name** (string): Unique name within this server’s scope (e.g., `"start_game"`).  
- **description** (string): Brief text describing what this action does.  
- **parameters** (array): A list of parameter definitions required by this action.
  - Each parameter has:
    - **name**: The parameter name (key).
    - **type**: The expected Python-type of the parameter, e.g. `"str"` or `"int"`.
    - **description**: Explains what the parameter is for, including ranges or usage details.
- **check** (object): A step to verify feasibility before running the action.  
- **init** (object, optional): A step to do any necessary setup.  
- **run** (object): The main step to perform the action.  

#### check/init/run Fields

Each step (check, init, run) specifies:

- **method**: `"ssh"` or `"http"`, indicating how to call it.
  - If `"ssh"`, expects a `command` to be executed.
  - If `"http"`, expects an `endpoint` to be requested (by default, a GET request unless otherwise implemented).
- **command** (string, only for `ssh`): The shell command to run on the remote host.
- **endpoint** (string, only for `http`): The URL for the REST call.

#### Example Action Definition

```yaml
actions:
  - name: "start_game"
    description: "Starts a game on the Steamdeck"
    parameters:
      - name: "game_path"
        type: "str"
        description: "Absolute path to the game’s executable or launch script."
      - name: "additional_option"
        type: "int"
        description: "Optional numeric parameter (range 1-10)."
    check:
      method: "ssh"
      command: "ps aux | grep my_game"
    init:
      method: "ssh"
      command: "mkdir -p /home/deck/game_temp"
    run:
      method: "ssh"
      command: "cd /home/deck/game_dir && ./start_game.sh"
```

---

### 3. Functions (High-Level Action Sequences)

The **functions** array allows you to define workflows that chain multiple actions—possibly across different servers. Each function has:

- **name** (string): Unique identifier for the function.  
- **description** (string): Explains the overall purpose.  
- **steps** (array): Ordered sequence of steps that each reference:
  - **server** (string): Which server name to target from `optional_services`.
  - **action** (string): Which action name to perform on that server.
  - **parameters** (object, optional): Key-value pairs for overriding or providing parameter values for that action. If missing, you (or your code) can prompt the user for them at runtime.

#### Example Function Definition

```yaml
functions:
  - name: "update_all_and_start_game"
    description: "Updates the Raspberry Pi and then starts a game on the Steamdeck."
    steps:
      - server: "raspberry"
        action: "update_system"
        parameters:
          update_channel: "stable"

      - server: "steamdeck"
        action: "pre_setup"

      - server: "steamdeck"
        action: "start_game"
        # If parameters are not defined, they will be asked from the user at runtime
        # parameters:
        #   game_path: "/home/deck/my_game.sh"
        #   additional_option: 2
```

Here, we see a sequence of three steps:
1. **Raspberry** → runs `update_system` action (with `update_channel`=`stable`).  
2. **Steamdeck** → runs `pre_setup`.  
3. **Steamdeck** → runs `start_game`.  

If `start_game` requires parameters (like `game_path` or `additional_option`) but they’re not provided, you can ask the user at runtime or assign a default.

---

## Usage in Python

1. **SystemStatus** can load this file (if present) under the key `"optional_services"` to perform connectivity checks.  
2. The **ActionsOrchestrator** parses the file to:
   - List servers (targets).
   - List actions per target.
   - Execute actions (including check → init → run steps).
   - Follow the sequences in `functions`.
   - 
They are used by burr_actions to perform actions in the burr graph.

### If the File is Missing
- When this YAML file is **not** found or is empty, `SystemStatus` only performs checks on **mandatory** services (STT, TTS, LLM). No optional checks or actions will be processed.

---

## Final Notes

- **optional_services** and **functions** can be maintained in a **single** YAML file.  
- Each server can have multiple **actions**.  
- Each **action** can define **parameters**, which your code may prompt the user for or fill in automatically.  
- **functions** are optional but allow chaining multiple actions in one high-level call.  

By centralizing these definitions in YAML, you can modify or add new actions without changing Python code.

#### Behavior if the File Is Missing

If the **optional_services.yaml** file is not present or contains no entries, no additional services are checked. The application will then only test the mandatory services (STT, TTS, and LLM).

## Links / unfinished stuff

* https://github.com/matatonic/openedai-speech
* https://github.com/DigitalPhonetics/IMS-Toucan
* https://github.com/thorstenMueller/Thorsten-Voice
