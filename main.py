import threading
import asyncio
import nltk
import re
from threading import Event

from burr.examples.streamlit.application import logger
from nltk.tokenize import sent_tokenize
from typing import Tuple, Generator, Optional, AsyncGenerator
from burr.core import ApplicationBuilder, State, when, expr
from burr.core.action import streaming_action, action
from servant.servant_factory import ServantFactory
from dotenv import load_dotenv
from enum import Enum

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
    full_text = ''
    try:
        factory.tts_provider.wait_until_done()
        # wait for wakeword, then stream the wave to the STT provider and steam back the transcription
        async for text in factory.human_speech_agent.get_human_input(
                ext_stop_signal=stop_signal,
                wait_for_wakeword=wait_for_wakeword
            ):
            full_text += text
            yield {"transcription_input": text}, None
    except KeyboardInterrupt as e:
        raise e
    except BaseException as e:
        logger.error("got error", exc_info=True)
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
    chat_item = {"content": prompt, "role": "user"}
    title(f"human_input: {prompt}")
    return {"prompt": prompt}, state.update(prompt=prompt).append(chat_history=chat_item)

@action(reads=["input_loop_counter"], writes=["input_loop_counter"])
def we_did_not_understand(state: State) -> Tuple[dict, State]:
    title("We did not understand")
    counter = state.get("input_loop_counter")
    if counter is None:
        counter=1
    else:
        counter += 1
    factory.human_speech_agent.engage_input_beep()
    return {"input_loop_counter": counter}, state.update(input_loop_counter=counter)

@action(reads=[], writes=["chat_history", "input_loop_counter"])
def exit_chat(state: State) -> Tuple[dict, State]:
    title("exit_chat")
    factory.human_speech_agent.say(f"Ich habe den Live Chat Modus beendet und unseren Chat geleert.")
    factory.human_speech_agent.say(f"Um mich wieder zu aktivieren sage das Wort {factory.va_provider.wakeword}.")
    factory.tts_provider.wait_until_done()
    return {"chat_history": [], "input_loop_counter": 0}, state.update(chat_history=[]).update(input_loop_counter=0)

@streaming_action(reads=["chat_history"], writes=["response", "sentences" , "chat_history", "input_loop_counter"])
async def ai_response(state: State, stop_signal: threading.Event) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    factory.human_speech_agent.processing_sound()
    # give the history including the last user input to the LLM to get its response
    response_stream = factory.llm_provider.chat_stream(state["chat_history"])
    print("KI: ", end='', flush=True)
    # consume the stream and collect response while printing to console
    response = ""
    sentences_list = []
    buffer = ''
    first_sentence_ready=False
    async for chunk in response_stream:
        response += chunk
        # identify sentences on-the-fly out of the stream
        # but first clean the string from newline chars. Add a . to each
        buffer = f"{buffer}{chunk}".replace('\n','. ')
        # remove the point we added if there is a mark char before
        buffer = re.sub(r'([?:!.,])\.', r'\1', buffer)
        # insert a space between sentences with no whitespace but a .
        buffer = re.sub(r"(?<!\d)\.(?![\d\s])", ". ", buffer)
        # remove all enumeration fragements (.1. and so on)
        buffer = re.sub(r'\.\d+\.', '.', buffer)
        # Tokenize to sentences
        sentences = sent_tokenize(text=buffer, language="german")
        #print(f"buffer (arr={len(sentences)}): {buffer} ")
        for sentence in sentences[:-1]:
            # clean the sentence from markdown and skip if broken
            sentence =  re.sub(r'[*_#`]+', '', sentence).strip()
            # process only if it has real chars
            if re.search(r'[A-Za-z0-9äöüÄÖÜß]', sentence) is None:
                continue
            if first_sentence_ready:
                factory.human_speech_agent.say(sentence)
            else:
                first_sentence_ready = True
                factory.human_speech_agent.skip_all_and_say(sentence)
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
    title(f"ai_response finished: response={response}")
    print("SENTENCE LIST:")
    for s in sentences_list:
        print(f" - {s}")
    # wait until TTS and soundcard finished playback
    factory.tts_provider.wait_until_done()
    yield ({"response": response, "sentences": sentences_list, "input_loop_counter": 0},
           state.update(response=response)
               .update(sentences=sentences_list)
               .update(input_loop_counter=0)
               .append(chat_history={"content": response, "role": "assistant"}))


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
            #
            # NORMAL LLM USER CHAT
            #
            # else pass on to use this as human input prompt
            ("choose_mode", "human_input", when(mode=Mode.CHAT)),
            # the human input is given to the LLM to get a response
            ("human_input", "ai_response"),
            # send the AI response split_sentence to split the stream into sentence pieces
            ("ai_response", "get_user_speak_input"),
            # get speak input from user without wake word (immediately record)
            ("get_user_speak_input", "choose_mode"),
            #
            # SPEAK INPUT IS GARBAGE
            #
            ("choose_mode", "we_did_not_understand", when(mode=Mode.GARBAGE_INPUT)),
            # directly go back to record again. Cycle until we have something
            ("we_did_not_understand", "get_user_speak_input", expr(f"input_loop_counter < 10")),
            # if we get no useful input than to back to wake word mode
            ("we_did_not_understand", "exit_chat"),
            #
            # END NORMAL LLM CHAT CYCLE (BACK TO WAKE WORD)
            #
            # if user wants to end the conversation we go back to listen to the wake word
            ("choose_mode", "exit_chat", when(mode=Mode.EXIT)),
            ("exit_chat", "wait_for_user_speak_input")
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
        halt_after=[],
        halt_before=[]
    )
    print(f"result={stream_result} action={last_action}")
    async for item in stream_result:
        if "sentences" in item.keys():
            print("FINAL: sentences="+item["sentences"], end="\n")
        else:
            print(f"FINAL: item={item}")
    #result = await result.get()
    title("Application finished")


async def main():
    app = application()
    try:
        print("Store graph.png of actual flow.")
        app.visualize(
            output_file_path="graph", include_conditions=True, view=False, format="png"
        )
    except:
        print("Graphviz is not installed, skip generating graph image.")
    await run(app)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print("Exit application with KeyboardInterrupt")
