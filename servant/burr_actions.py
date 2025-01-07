import threading
import re
import json
from threading import Event
from enum import Enum
from servant.llm.llm_prompt_manager_interface import Mode
from burr.examples.streamlit.application import logger
from nltk.tokenize import sent_tokenize
from typing import Tuple, Optional, AsyncGenerator
from burr.core import State
from burr.core.action import streaming_action, action
from servant.philips_wiz import wiz_set_state, wiz_get_state
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

@streaming_action(reads=['response'], writes=['input_ok', 'command'])
async def mode_led_human_input(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    response = state["response"]
    # We have some text input, now decide what mode we need using the LLM
    # check if it is valid json
    json_cmd = response.strip().replace("\'", "\"")
    print(f"\n\nJSON: >{json_cmd}<\n\n")
    parsed_command = json.loads(json_cmd)
    if 'action' in parsed_command:
        input_ok = parsed_command['action'].lower() != 'invalid'
    else:
        input_ok = True
    if not input_ok:
        factory.human_speech_agent.say("Ich habe noch zu wenig informationen, was soll ich mit dem Licht machen?")
    else:
        try:
            await wiz_set_state(parsed_command)
            msg = f"Beleuchtung wurde angepasst"
            #for p in  parsed_command.keys():
            #    msg += f"{p} zu {parsed_command[p]}\n"
            factory.human_speech_agent.say(msg)
            title(f"mode_led_human_input: {msg}")
        except:
            factory.human_speech_agent.beep_error()
            factory.human_speech_agent.say("Ein Fehler ist aufgetreten als ich das Licht verändern wollte.")
    yield ({'command': json.dumps(parsed_command), 'input_ok': input_ok},
            state.update(command=json_cmd).update(input_ok=input_ok))

@streaming_action(reads=[], writes=[m.name for m in StateKeys])
async def entry_point(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    Init all state variables with StateKeys enum
    """
    title("entry_point: greeting the user")
    factory.human_speech_agent.say_init_greeting()
    factory.human_speech_agent.wait_until_talking_finished()
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

@action(reads=["input_loop_counter", "prompt", "mode"], writes=["input_loop_counter"])
async def we_did_not_understand(state: State) -> Tuple[dict, State]:
    #TODO: implement that we use some state string we say to the user if filled
    counter = state.get("input_loop_counter")
    mode = state[StateKeys.mode.name]
    title(f"we_did_not_understand: input_loop_counter={counter} mode={mode}")
    if counter is None:
        counter=1
    else:
        counter += 1
    factory.human_speech_agent.engage_input_beep()
    return {"input_loop_counter": counter}, state.update(input_loop_counter=counter)

@action(reads=["mode"], writes=["mode", "chat_history", "input_loop_counter", "prompt", "command"])
async def exit_mode(state: State) -> Tuple[dict, State]:
    mode = state["mode"]
    title("exit_mode: "+mode)
    if mode == Mode.CHAT:
        # say something to the user
        factory.human_speech_agent.say(f"Ich habe den Live Chat Modus beendet und unseren Chat geleert.")
        factory.human_speech_agent.say(f"Um mich wieder zu aktivieren sage das Wort {factory.va_provider.wakeword}.")
        factory.human_speech_agent.wait_until_talking_finished()
    prompt_manager = factory.llm_provider.get_prompt_manager()
    # clear history of the current mode chat
    prompt_manager.empty_history()
    return ({"mode": Mode.MODUS_SELECTION.name, "chat_history": [], "input_loop_counter": 0, "prompt": "", "command": ""},
            state.update(mode=Mode.MODUS_SELECTION.name).update(chat_history=[]).update(input_loop_counter=0).update(command="").update(prompt=""))

@streaming_action(reads=["transcription_input","mode"], writes=["input_loop_counter", "mode", "chat_history", "input_ok"])
async def choose_mode(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # first of all collect the results from the stream (breaking stream here)
    full_text = state["transcription_input"]
    # make easy check if input is a valid sentence at all
    if not is_sane_input_german(full_text) or len(full_text.strip())<3:
        # if we got no useful string then directly return
        yield {"input_ok": False}, state.update(input_ok=False)
    # We have some text input, now decide what mode we need using the LLM
    prompt_manager = factory.llm_provider.get_prompt_manager()
    prompt_manager.set_mode(Mode.MODUS_SELECTION)
    prompt_manager.empty_history()
    prompt_manager.add_user_entry(full_text)
    print(prompt_manager.pretty_print_history())
    full_res = ''
    async for res in factory.llm_provider.chat(prompt_manager.get_history()):
        print(f"{res}")
        full_res += res
    try:
        # check for uppercase mode name
        m = get_mode_from_str(full_res)
        # check if the mode has been changed
        if m.name != state[StateKeys.mode.name]:
            # if it has changed then empty the history
            prompt_manager.empty_history()
        if m.name == Mode.GARBAGEINPUT.name:
            # do not change the mode itself if input is not ok
            title(f"choose_mode: got GARBAGE_INPUT: {full_res} instead of a useful mode")
            yield {"input_ok": False}, state.update(input_ok=False)
        else:
            # else return the mode itself and new history
            # switch the mode of the prompt manager
            title(f"choose_mode: {m.name}")
            prompt_manager.set_mode(m)
            yield ({"input_ok": True, "mode": m.name, "input_loop_counter": 0},
                state.update(input_loop_counter=0).update(mode=m.name).update(input_ok=True).update(chat_history=prompt_manager.get_history()))
    except Exception as e:
        logger.error("Got exception in MODE SELECTION", exc_info=True)
        title(f"choose_mode: Got exception in MODE SELECTION")
        yield ({"input_ok": False, "input_loop_counter": 0},
               state.update(input_loop_counter=0).update(input_loop_counter=0).update(input_ok=False).update(chat_history=prompt_manager.get_history()))

@streaming_action(reads=["mode"], writes=["transcription_input"])
async def get_user_speak_input(state: State, wait_for_wakeword: bool = True) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    This action blocks until it detects the wakeword from the microphone stream. It then
    passes data as wav byte stream to voice_buffer so it can be streamed to transcription
    """
    mode = state[StateKeys.mode.name]
    title(f"get_user_speak_input: recording and transcribe. wake word={wait_for_wakeword} mode={mode}")
    full_text = ''
    try:
        factory.tts_provider.wait_until_done()
        # wait for wakeword, then stream the wave to the STT provider and steam back the transcription
        async for text in factory.human_speech_agent.get_human_input(
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
    title(f"check_if_input_is_garbage: {input_str}, input_ok={input_ok}")
    yield {"input_ok": input_ok}, state.update(input_ok=input_ok)

@action(reads=["transcription_input","mode"], writes=["prompt", "chat_history"])
async def human_input(state: State) -> Tuple[dict, State]:
    # add the prompt to history (we have no streaming yield, directly yield the final return)
    prompt = state.get(StateKeys.transcription_input.name)
    mode = state.get(StateKeys.mode.name)
    if mode == Mode.LEDCONTROL.name:
        state_dict = await wiz_get_state()
        current_led_state = json.dumps(state_dict)
        prompt = f"Aktueller Licht status: {current_led_state}\n\n{prompt}"
    factory.llm_provider.get_prompt_manager().add_user_entry(prompt)
    title(f"human_input({mode}): {prompt}")
    # overwrite the current history with the prompt manager one
    return ({"prompt": prompt},
            state.update(prompt=prompt).update(chat_history=factory.llm_provider.get_prompt_manager().get_history()))

@streaming_action(reads=["chat_history", "mode"], writes=["response", "sentences" , "chat_history", "input_loop_counter"])
async def ai_response(state: State, stop_signal: threading.Event) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    factory.human_speech_agent.processing_sound()
    # give the history including the last user input to the LLM to get its response
    history = state[StateKeys.chat_history.name]
    mode = state[StateKeys.mode.name]
    response_stream = factory.llm_provider.chat(history)
    title(f"ai_response: Start generation")
    print("KI: ", end='', flush=True)
    modes_with_speech_output = [Mode.CHAT.name]
    # consume the stream and collect response while printing to console
    response = ""
    sentences_list = []
    buffer = ''
    first_sentence_ready=False
    # reset the given stop_signal
    stop_signal.clear()
    if mode == Mode.CHAT.name:
        factory.human_speech_agent.start_speech_interrupt_thread(ext_stop_signal=stop_signal)
    async for chunk in response_stream:
        response += chunk
        # stop if the signal from speech interruption thread arrives
        if stop_signal.is_set():
            response+=".\nStopped generation because user ordered to do so."
            break
        # only parse sentences and send them to TTS when we are
        # in the defined modes to do so
        if mode in modes_with_speech_output:
            # identify sentences on-the-fly out of the stream
            buffer = clean_str_from_markdown(f"{buffer}{chunk}")
            # Tokenize to sentences
            sentences = sent_tokenize(text=buffer, language="german")
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
        else:
            logger.debug(f"Do not send to text-to-speech because we are in mode {mode}")
    if mode in modes_with_speech_output:
        # send the last sentence now
        if len(buffer) > 0:
            sentences_list.append(buffer)
            factory.human_speech_agent.say(buffer)
            yield {"sentences": buffer}, None
        for s in sentences_list:
            print(f" - {s}")
    # Update state after stream is finished
    title(f"ai_response finished: response={response}")
    chat_entry = factory.llm_provider.get_prompt_manager().add_assistant_entry(response)
    logger.debug(factory.llm_provider.get_prompt_manager().pretty_print_history())
    factory.human_speech_agent.wait_until_talking_finished()
    yield ({"response": response, "sentences": sentences_list, "input_loop_counter": 0},
           state.update(response=response)
               .update(sentences=sentences_list)
               .update(input_loop_counter=0)
               .append(chat_history=chat_entry))

@action(reads=["mode"], writes=[])
async def ai_response_finished(state: State) ->  Tuple[dict, State]:
    mode = state[StateKeys.mode.name]
    title(f"ai_response_finished: mode={mode}")
    # wait until TTS and soundcard finished playback
    factory.human_speech_agent.wait_until_talking_finished()
    if mode == Mode.CHAT.name:
        # exit the speech-interruption thread, wait until it has shutdown
        factory.human_speech_agent.stop_speech_interrupt_thread()
    return {}, state