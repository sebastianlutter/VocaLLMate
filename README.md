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
# Start stacks for CPU
./stacks.sh start
# Start stacks for CUDA/NVIDIA
./stacks.sh start cuda
# Stop the stack
./stacks.sj stop [cuda]
```

## The application

* First create a venv and install dependencies
```
python3 -mvenv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

* Then run application
```
python3 main.py
```