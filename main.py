import threading
import time
import random
import asyncio
import nltk
from threading import Event
from nltk.tokenize import sent_tokenize
from typing import Generator, List
from typing import Tuple, Generator, Optional, AsyncGenerator
from burr.core import ApplicationBuilder, State, when, expr
from burr.core.action import streaming_action, action
from servant.human_speech_agent import HumanSpeechAgent
from servant.servant_factory import ServantFactory
from dotenv import load_dotenv
from enum import Enum

#
# TODO: Directly start recording after wakeword, do not wait until websocket is connected
# TODO: Make an external stop signal that is given to all components instead of each has a own (or maybe it makes sense)
#

nltk.download('punkt_tab')

load_dotenv()

class Mode(Enum):
    EXIT=1
    GARBAGE_INPUT=2
    CHAT=3

first_run = True
factory = ServantFactory()

def title(msg):
    print("###########################################################################################################")
    print(f"# {msg}")
    print("###########################################################################################################")

@streaming_action(reads=[], writes=[])
async def entry_point(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    This is a kind of init. And greed the user when everything is done
    """
    factory.human_speech_agent.say_init_greeting()
    yield {}, state

@streaming_action(reads=[], writes=["transcription_input"])
async def get_user_speak_input(state: State, stop_signal: Event, wait_for_wakeword: bool = True) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    This action blocks until it detects the wakeword from the microphone stream. It then
    passes data as wav byte stream to voice_buffer so it can be streamed to transcription
    """
    # wait for wakeword, then stream the wave to the STT provider and steam back the transcription
    full_text = ''
    async for text in factory.human_speech_agent.get_human_input(
            ext_stop_signal=stop_signal,
            wait_for_wakeword=wait_for_wakeword
        ):
        full_text += text
        yield {"transcription_input": text}, None
    title(f"get_user_speak_input: {full_text}")
    # when all is done update state
    yield {"transcription_input": full_text}, state.update(transcription_input=full_text)

@streaming_action(reads=["transcription_input"], writes=["mode"])
async def choose_mode(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # first of all collect the results from the stream (breaking stream here)
    full_text = state["transcription_input"]
    # now decide what we want to do
    if len(full_text) < 15:
        m = Mode.GARBAGE_INPUT
    elif factory.llm_provider.is_conversation_ending(full_text):
        m = Mode.EXIT
    else:
        m = Mode.CHAT
    title(f"choose_mode: {m}")
    yield {"mode": m}, state.update(mode=m)

@action(reads=["transcription_input"], writes=["prompt", "chat_history"])
async def human_input(state: State) -> Tuple[dict, State]:
    # add the prompt to history (we have no streaming yield, directly yield the final return)
    prompt = state.get("transcription_input")
    print(f"Human Input: {prompt}")
    chat_item = {"content": prompt, "role": "user"}
    title(f"human_input: {prompt}")
    return {"prompt": prompt}, state.update(prompt=prompt).append(chat_history=chat_item)

@action(reads=["transcription_input"], writes=["transcription_input"])
def we_did_not_understand(state: State) -> Tuple[dict, State]:
    title("We did not understand")
    factory.human_speech_agent.beep_error()
    #factory.human_speech_agent.say_did_not_understand()
    return {"transcription_input": ''}, state.update(transcription_input='')

@action(reads=[], writes=["chat_history"])
def exit_chat(state: State) -> Tuple[dict, State]:
    title("exit_chat")
    factory.human_speech_agent.say_bye("Ich beende das Programm")
    return {"chat_history": []}, state.update(chat_history=[])

@streaming_action(reads=["chat_history"], writes=["response", "sentences" , "chat_history"])
async def ai_response(state: State, stop_signal: threading.Event) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # give the history including the last user input to the LLM to get its response
    response_stream = factory.llm_provider.chat_stream(state["chat_history"])
    print("KI: ", end='', flush=True)
    # consume the stream and collect response while printing to console
    response = ""
    sentences_list = []
    buffer = ''
    async for chunk in response_stream:
        response += chunk
        # identify sentences on-the-fly out of the stream
        # process all full sentences (except incomplete)
        buffer = f"{buffer}{chunk}"
        # Tokenize to sentences
        sentences = sent_tokenize(text=buffer, language="german")
        #print(f"buffer (arr={len(sentences)}): {buffer} ")
        for sentence in sentences[:-1]:
            factory.human_speech_agent.say(sentence)
            sentences_list.append(sentence)
            yield { "sentences": sentence }, None
        # store last (maybe incomplete) sentence in the buffer
        buffer = sentences[-1]
        print(chunk, end='', flush=True)
        # No state update on intermediate results
        yield { "response": chunk }, None
    # send the last sentence now
    if len(buffer) > 0:
        sentences_list.append(buffer)
        factory.human_speech_agent.say(buffer)
        yield { "sentences": buffer }, None
    # Update state after stream is finished
    print()
    title(f"ai_response finished: response={response}\nsentence_list={sentences_list}")
    #factory.human_speech_agent.say(response)
    yield {"response": response, "sentences": sentences_list}, state.update(response=response).update(sentences=sentences_list).append(chat_history={"content": response, "role": "assistant"})


def application():
    stop_signal = threading.Event()
    return (
        ApplicationBuilder()
        .with_actions(
            wait_for_user_speak_input=get_user_speak_input.bind(
                stop_signal=stop_signal,
                wait_for_wakeword=True
            ),
            get_user_speak_input=get_user_speak_input.bind(
                stop_signal=stop_signal,
                wait_for_wakeword=False
            ),
            we_did_not_understand=we_did_not_understand,
            human_input=human_input,
            ai_response=ai_response.bind(stop_signal=stop_signal),
            choose_mode=choose_mode,
            exit_chat=exit_chat,
            entry_point=entry_point
        )
        .with_transitions(
            # entrypoint action
            ("entry_point","wait_for_user_speak_input"),
            # get first user input with wakeup word "hey computer" and send to transcription
            ("wait_for_user_speak_input", "choose_mode"),
            # check if we have enough chars from the transcription, if not go to we_did_not_understand
            ("choose_mode", "we_did_not_understand", when(mode=Mode.GARBAGE_INPUT)),
            # give user speech feedback and directly records afterwards
            ("we_did_not_understand", "wait_for_user_speak_input"),
            # if user wants to end the conversation we do so
            ("choose_mode", "exit_chat", when(mode=Mode.EXIT)),
            # else pass on to use this as human input prompt
            ("choose_mode", "human_input", when(mode=Mode.CHAT)),
            # the human input is given to the LLM to get a response
            ("human_input", "ai_response"),
            #("ai_response", "wait_for_user_speak_input"),
             # send the AI response split_sentence to split the stream into sentence pieces
            ("ai_response", "wait_for_user_speak_input"),
        )
        # init the chat history with the system prompt
        .with_state(chat_history=[{"content": factory.llm_provider.system_prompt, "role": "assistant"}], exit_chat=False)
        .with_entrypoint("entry_point")
        .with_tracker("local", project="servant-llm")
        .build()
    )

async def run(app):
    """Runs the application. Queries the input for prompt"""
    last_action, stream_result = await app.astream_result(
        halt_after=["exit_chat"]
    )
    print(f"result={stream_result} action={last_action}")
    async for item in stream_result:
        print("FINAL: Got "+item["sentences"], end="\n")
    #result = await result.get()
    title("Application finished")


async def main():
    app = application()
    try:
        print("Store graph.png of actual flow.")
        app.visualize(
            output_file_path="graph", include_conditions=False, view=False, format="png"
        )
    except:
        print("Graphviz is not installed, skip generating graph image.")
    await run(app)

if __name__ == "__main__":
    asyncio.run(main())