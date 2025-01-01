from dotenv import load_dotenv
load_dotenv()
import threading
import asyncio
import nltk
from burr.core.action import streaming_action
from burr.core import State
from servant.llm.llm_prompt_manager_interface import Mode
from burr.core import ApplicationBuilder, when, expr
from typing import Tuple, Optional, AsyncGenerator
from servant.utils import title
from servant.burr_actions import get_user_speak_input, we_did_not_understand, human_input
from servant.burr_actions import choose_mode, exit_chat, ai_response
from enum import Enum
nltk.download('punkt_tab')

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
    response = ''

@streaming_action(reads=[], writes=[m.name for m in StateKeys])
async def entry_point(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    Init all state variables with StateKeys enum
    """
    yield ({ m.name: m.value for m in StateKeys }, state.update(
        chat_history=StateKeys.chat_history.value,
        transcription_input=StateKeys.transcription_input.value,
        exit_chat=StateKeys.exit_chat.value,
        input_loop_counter=StateKeys.input_loop_counter.value,
        mode=StateKeys.mode.value,
        prompt=StateKeys.prompt.value,
        response=StateKeys.response.value
    ))


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
            get_mode_speak_input=get_user_speak_input.bind(
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
#        .with_state(chat_history=[], exit_chat=False, input_loop_counter=0)
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
