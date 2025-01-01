import threading
import re
from importlib.metadata import entry_points
from threading import Event
from servant.llm.llm_prompt_manager_interface import Mode
from burr.examples.streamlit.application import logger
from nltk.tokenize import sent_tokenize
from typing import Tuple, Optional, AsyncGenerator
from burr.core import State
from burr.core.action import streaming_action, action
from servant.utils import title, clean_str_from_markdown, is_conversation_ending
from servant.servant_factory import ServantFactory

first_run = True
factory = ServantFactory()

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

@streaming_action(reads=["transcription_input"], writes=["mode"])
async def choose_mode(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # first of all collect the results from the stream (breaking stream here)
    full_text = state["transcription_input"]
    # now decide what we want to do
    prompt_manager = factory.llm_provider.get_prompt_manager()
    prompt_manager.set_mode(Mode.MODUS_SELECTION)
    prompt_manager.empty_history()
    prompt_manager.add_user_entry(full_text)
    full_res = ''
    async for res in factory.llm_provider.chat(prompt_manager.get_history()):
        print(f"{res}")
        full_res += res
    m = None
    # check for uppercase mode name
    for mode in Mode:
        if mode.name in full_res:
            m=mode.name
            break
    title(f"choose_mode: {m}")
    yield {"mode": m}, state.update(mode=m)

@streaming_action(reads=["transcription_input"], writes=["mode"])
async def choose_mode_old(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    # first of all collect the results from the stream (breaking stream here)
    full_text = state["transcription_input"]
    # now decide what we want to do
    if len(full_text) < 15:
        m = Mode.GARBAGE_INPUT
    elif is_conversation_ending(full_text):
        m = Mode.EXIT
    else:
        m = Mode.CHAT
    title(f"choose_mode: {m}")
    yield {"mode": m}, state.update(mode=m)

@action(reads=["transcription_input"], writes=["prompt", "chat_history"])
async def human_input(state: State) -> Tuple[dict, State]:
    # add the prompt to history (we have no streaming yield, directly yield the final return)
    prompt = state.get("transcription_input")
    chat_item = factory.llm_provider.get_prompt_manager().add_user_entry(prompt)
    prompt = chat_item["content"]
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
    factory.llm_provider.get_prompt_manager().empty_history()
    return {"chat_history": [], "input_loop_counter": 0}, state.update(chat_history=[]).update(input_loop_counter=0)

@streaming_action(reads=["chat_history"], writes=["response", "sentences" , "chat_history", "input_loop_counter"])
async def ai_response(state: State, stop_signal: threading.Event) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    stop_signal.clear()
    factory.human_speech_agent.processing_sound()
    # give the history including the last user input to the LLM to get its response
    response_stream = factory.llm_provider.chat(state["chat_history"])
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