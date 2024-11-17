import re
from ollama import Client
from typing import Tuple
from burr.core import ApplicationBuilder, State, action, when
from servant.utils import get_speech_input
from servant.tts import TextToSpeechService

#tts_service = TextToSpeechService()

@action(reads=["chat_history"], writes=["prompt", "chat_history"])
def human_input(state: State) -> Tuple[dict, State]:
    print("#########################################################################")
    while True:
        # wait for wake-word and transcribe the recorded user voice
        prompt = get_speech_input()
        if prompt.strip():
            break
        else:
            print("Got no user input, waiting for input again")
    # add the prompt to history
    print(f"User: {prompt}")
    chat_item = {"content": prompt, "role": "user"}
    return {"prompt": prompt}, state.update(prompt=prompt).append(chat_history=chat_item)

@action(reads=["chat_history"], writes=["response", "chat_history"])
def ai_response(state: State) -> Tuple[dict, State]:
    client = Client(host="http://127.0.0.1:11434")
    content = (
        client.chat(
            model='llama3.2',
            stream=True,
            messages=state["chat_history"],
        )
    )
    # collect response while printing it from stream
    response = ''
    # collect sentences to send them to tts early
    sentence_buffer = ""
    print("KI: ", end='', flush=True)
    for chunk in content:
        c = chunk['message']['content']
        print(c, end='', flush=True)
        sentence_buffer += c.replace('\n',' ')
        response += c
    chat_item = {"content": response, "role": "assistant"}
    return {"response": response}, state.update(response=response).append(chat_history=chat_item)

def application():
    return (
        ApplicationBuilder()
        .with_actions(
            human_input=human_input,
            ai_response=ai_response,
        )
        .with_transitions(
            ("human_input", "ai_response"),
            ("ai_response", "human_input"),
        )
        .with_state(chat_history=[])
        .with_entrypoint("human_input")
        .with_tracker("local", project="servant-llm")
        .build()
    )

if __name__ == "__main__":
    app = application()
    action_we_ran, result, state = app.run()
    print("Application finished")
    for item in state['chat_history']:
        print(item['role'] + ':' + item['content'] + '\n')