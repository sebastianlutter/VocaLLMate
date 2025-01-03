import threading
import re
import json
from threading import Event
from enum import Enum

from click import command

from servant.llm.llm_prompt_manager_interface import Mode
from burr.examples.streamlit.application import logger
from nltk.tokenize import sent_tokenize
from typing import Tuple, Optional, AsyncGenerator
from burr.core import State
from burr.core.action import streaming_action, action
from servant.utils import title, clean_str_from_markdown, is_conversation_ending, is_sane_input_german
from servant.servant_factory import ServantFactory

first_run = True
factory = ServantFactory()


class StateKeys(Enum):
    """
    An Enum to keep all possible state variable names in one place
    and to give em init values
    """
    chat_history = {},
    transcription_input = ''
    exit_chat = False
    input_loop_counter = 0
    mode = Mode.MODUS_SELECTION.name
    prompt = ''
    input_ok = True
    response = ''
    command = ''

def get_mode_from_str(str: str):
    for mode in Mode:
        if mode.name in str:
            return mode
    raise Exception(f"Did not find \"{str}\" in Mode enum.")

@streaming_action(reads=['prompt'], writes=['input_ok', 'command'])
async def mode_led_human_input(state: State) -> Tuple[dict, Optional[State]]:
    #TODO: check if we get everything we need to do a LED command
    prompt = state["prompt"]
    # We have some text input, now decide what mode we need using the LLM
    prompt_manager = factory.llm_provider.get_prompt_manager()
    prompt_manager.add_user_entry(prompt)
    full_res = ''
    async for res in factory.llm_provider.chat(prompt_manager.get_history()):
        print(f"{res}")
        full_res += res
    # check if it is valid json
    parsed_command = json.loads(full_res.strip())
    input_ok= parsed_command['action'].lower() != 'invalid'
    # TODO: control the LED here! Or add a own action?!?
    title(f"LED set: {command}")
    return ({'command': parsed_command, 'input_ok': input_ok},
            state.update(command=prompt).update(input_ok=input_ok))

@streaming_action(reads=[], writes=[m.name for m in StateKeys])
async def entry_point(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    Init all state variables with StateKeys enum
    """
    factory.human_speech_agent.say_init_greeting()
    yield ({ m.name: m.value for m in StateKeys }, state.update(
        chat_history=StateKeys.chat_history.value,
        transcription_input=StateKeys.transcription_input.value,
        exit_chat=StateKeys.exit_chat.value,
        input_loop_counter=StateKeys.input_loop_counter.value,
        mode=StateKeys.mode.value,
        prompt=StateKeys.prompt.value,
        response=StateKeys.response.value,
        input_ok=True,
        command=""
    ))

@action(reads=["input_loop_counter"], writes=["input_loop_counter"])
def we_did_not_understand(state: State) -> Tuple[dict, State]:
    #TODO: implement that we use some state string we say to the user if filled
    title("We did not understand")
    counter = state.get("input_loop_counter")
    if counter is None:
        counter=1
    else:
        counter += 1
    factory.human_speech_agent.engage_input_beep()
    return {"input_loop_counter": counter}, state.update(input_loop_counter=counter)

@action(reads=[], writes=["chat_history", "input_loop_counter"])
def exit_mode(state: State) -> Tuple[dict, State]:
    title("exit_chat")
    # say something to the user
    factory.human_speech_agent.say(f"Ich habe den Live Chat Modus beendet und unseren Chat geleert.")
    factory.human_speech_agent.say(f"Um mich wieder zu aktivieren sage das Wort {factory.va_provider.wakeword}.")
    factory.tts_provider.wait_until_done()
    prompt_manager = factory.llm_provider.get_prompt_manager()
    # clear history of the current mode chat
    prompt_manager.empty_history()
    return {"chat_history": [], "input_loop_counter": 0}, state.update(chat_history=[]).update(input_loop_counter=0)

@streaming_action(reads=["transcription_input","mode"], writes=["mode", "chat_history", "input_ok"])
async def choose_mode(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # first of all collect the results from the stream (breaking stream here)
    full_text = state["transcription_input"]
    # make easy check if input is a valid sentence at all
    if not is_sane_input_german(full_text):
        # if we got no useful string then directly return
        yield {"input_ok": False}, state.update(input_ok=False)
    # We have some text input, now decide what mode we need using the LLM
    prompt_manager = factory.llm_provider.get_prompt_manager()
    prompt_manager.set_mode(Mode.MODUS_SELECTION)
    prompt_manager.empty_history()
    prompt_manager.add_user_entry(full_text)
    full_res = ''
    async for res in factory.llm_provider.chat(prompt_manager.get_history()):
        print(f"{res}")
        full_res += res
    # check for uppercase mode name
    m = get_mode_from_str(full_res)
    # check if the mode has been changed
    if m.name != state[StateKeys.mode.name]:
        # if it has changed then empty the history
        prompt_manager.empty_history()
    if m.name == Mode.GARBAGEINPUT:
        # do not change the mode itself if input is not ok
        yield {"input_ok": False}, state.update(input_ok=False)
    else:
        # else return the mode itself and new history
        # switch the mode of the prompt manager
        title(f"choose_mode: {m.name}")
        prompt_manager.set_mode(m)
        yield ({"input_ok": True, "mode": m.name},
            state.update(mode=m.name).update(chat_history=prompt_manager.get_history()).update(input_ok=True))

@streaming_action(reads=[], writes=["transcription_input"])
async def get_user_speak_input(state: State, stop_signal: Event, wait_for_wakeword: bool = True) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    This action blocks until it detects the wakeword from the microphone stream. It then
    passes data as wav byte stream to voice_buffer so it can be streamed to transcription
    """
    stop_signal.clear()
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

@streaming_action(reads=["transcription_input"], writes=["input_ok"])
async def check_if_input_is_garbage(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    input_str = state[StateKeys.transcription_input.name]
    input_ok = is_sane_input_german(input_str)
    yield {"input_ok": input_ok}, state.update(input_ok=input_ok)

@action(reads=["transcription_input"], writes=["prompt", "chat_history"])
async def human_input(state: State) -> Tuple[dict, State]:
    # add the prompt to history (we have no streaming yield, directly yield the final return)
    prompt = state.get(StateKeys.transcription_input.name)
    factory.llm_provider.get_prompt_manager().add_user_entry(prompt)
    title(f"human_input: {prompt}")
    # overwrite the current history with the prompt manager one
    return ({"prompt": prompt},
            state.update(prompt=prompt).update(chat_history=factory.llm_provider.get_prompt_manager().get_history()))

@streaming_action(reads=["chat_history"], writes=["response", "sentences" , "chat_history", "input_loop_counter"])
async def ai_response(state: State, stop_signal: threading.Event) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    stop_signal.clear()
    factory.human_speech_agent.processing_sound()
    # give the history including the last user input to the LLM to get its response
    history = state["chat_history"]
    response_stream = factory.llm_provider.chat(history)
    print("KI: ", end='', flush=True)
    # consume the stream and collect response while printing to console
    response = ""
    sentences_list = []
    buffer = ''
    first_sentence_ready=False
    factory.human_speech_agent.start_speech_interrupt_thread(ext_stop_signal=stop_signal)
    async for chunk in response_stream:
        response += chunk
        # stop if the signal from speech interruption thread arrives
        if stop_signal.is_set():
            response+=".\nStopped generation because user ordered to do so."
            break
        # identify sentences on-the-fly out of the stream
        buffer = clean_str_from_markdown(f"{buffer}{chunk}")
        # Tokenize to sentences
        sentences = sent_tokenize(text=buffer, language="german")
        #print(f"buffer (arr={len(sentences)}): {buffer} ")
        for sentence in sentences[:-1]:
            # clean the sentence from markdown and skip if broken
            sentence =  re.sub(r'[*_#`"\']+', '', sentence).strip()
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
    chat_entry = factory.llm_provider.get_prompt_manager().add_assistant_entry(response)
    factory.llm_provider.get_prompt_manager().pretty_print_history()
    # wait until TTS and soundcard finished playback
    factory.tts_provider.wait_until_done()
    factory.tts_provider.soundcard.wait_until_playback_finished()
    yield ({"response": response, "sentences": sentences_list, "input_loop_counter": 0},
           state.update(response=response)
               .update(sentences=sentences_list)
               .update(input_loop_counter=0)
               .append(chat_history=chat_entry))