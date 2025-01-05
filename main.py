from dotenv import load_dotenv
load_dotenv()
import threading
import asyncio
import nltk
from nltk.corpus import swadesh
from burr.core.action import streaming_action
from burr.core import State
from servant.llm.llm_prompt_manager_interface import Mode
from burr.core import ApplicationBuilder, when, expr
from typing import Tuple, Optional, AsyncGenerator
from servant.utils import title
from servant.burr_actions import get_user_speak_input, we_did_not_understand, human_input, \
    check_if_input_is_garbage, StateKeys, choose_mode, exit_mode, ai_response, entry_point, mode_led_human_input

nltk.download('punkt_tab', quiet=True)
# Load German words from the Swadesh corpus
GERMAN_WORDS = set(word.lower() for word in swadesh.words('de'))


@streaming_action(reads=[], writes=[m.name for m in StateKeys])
async def error_exit_node(state: State) -> AsyncGenerator[Tuple[dict, Optional[State]], None]:
    """
    Exit node if error happened
    """
    yield {}, state


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
            check_if_input_is_garbage=check_if_input_is_garbage,
            we_did_not_understand=we_did_not_understand,
            mode_select_we_did_not_understand=we_did_not_understand,
            human_input=human_input,
            ai_response=ai_response.bind(stop_signal=stop_signal),
            choose_mode=choose_mode,
            exit_mode=exit_mode,
            entry_point=entry_point,
            mode_led_human_input=mode_led_human_input
        )
        .with_transitions(
            #
            # entrypoint action in CHOOSE_MODE setting
            #
            ("entry_point", "wait_for_user_speak_input"),
            # get first user input with wakeup word "hey computer" and send to transcription
            ("wait_for_user_speak_input", "choose_mode"),
            # when user input was gibberish or emtpy then again get user input (get into cycle)
            ("choose_mode", "mode_select_we_did_not_understand",
             expr(f'mode == "{Mode.GARBAGEINPUT.name}" or not input_ok')),
            # count up to ten in the cycle before you exit
            ("mode_select_we_did_not_understand", "get_mode_speak_input",
             expr(f'input_loop_counter < 10')),
#            # when we have more than 10 cycles to back to wake word (and thus to entrypoint)
            ("mode_select_we_did_not_understand", "exit_mode",
             expr(f'input_loop_counter >= 10')),
            # when we got input go to choose_mode again
            ("get_mode_speak_input", "choose_mode"),
            #
            # General ask the user cycle until we get something useful
            #
            # get speak input from user without wake word (immediately record)
            ("get_user_speak_input", "check_if_input_is_garbage"),
            # directly go back to record again. Cycle until we have something
            ("we_did_not_understand", "get_user_speak_input",
             expr(f'input_loop_counter < 10')),
            # check if input is sane
            ("check_if_input_is_garbage", "we_did_not_understand",
             expr(f'not input_ok')),
            # if input is usable go forward to step human_input
            ("check_if_input_is_garbage", "human_input",
             expr(f'input_ok')),
            # the human input is given to the LLM to get a response
            ("human_input", "ai_response"),
            # if we cycled ten times to get speak input without success exit the mode
            ("we_did_not_understand", "exit_mode",
             expr(f'input_loop_counter >= 10')),
            # and whenever we get to this node we start again from beginning
            ("exit_mode", "wait_for_user_speak_input"),
            #
            # NORMAL LLM USER CHAT
            #
            # when mode==CHAT then process and send input to LLM for talking
            ("choose_mode", "human_input",
             expr(f'mode == "{Mode.CHAT.name}" and input_ok')),
            # ask for input if we got no useful input
            ("choose_mode", "get_user_speak_input",
             expr(f'mode == "{Mode.LEDCONTROL.name}" and not input_ok')),
            # when we get AI response directly go back to the user for input
            ("ai_response", "get_user_speak_input",
             expr(f'mode == "{Mode.CHAT.name}"')),
            #
            # CONTROL LED/LIGHTS
            #
            # when mode==LEDCONTROL then process and send input to LLM for talking
            ("choose_mode", "human_input",
             expr(f'mode == "{Mode.LEDCONTROL.name}" and input_ok')),
            # get back to direct record
            ("choose_mode", "get_user_speak_input",
             expr(f'mode == "{Mode.LEDCONTROL.name}" and not input_ok')),
            # try to get a LED command from user prompt
            ("ai_response", "mode_led_human_input",
             expr(f'mode == "{Mode.LEDCONTROL.name}"')),
            # when the command was understood, and the LED has been altered exit this mode
            ("mode_led_human_input", "exit_mode",
              expr(f'input_ok')),
            # when the user input was not useful parseable and no command has been instruct the user
            ("mode_led_human_input", "we_did_not_understand",
             expr(f'not input_ok')),
            #
            # A catch all target if modus is not supported yet
            #
            ("choose_mode", "exit_mode",
             expr(f'not (mode in ["{Mode.MODUS_SELECTION.name}", "{Mode.CHAT.name}", ""])')),
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
