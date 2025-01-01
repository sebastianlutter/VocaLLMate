import re

from burr.core import State
from fuzzywuzzy import process

from main import StateKeys


def title(msg):
    print("###########################################################################################################")
    print(f"# {msg}")
    print("###########################################################################################################")

def is_conversation_ending(sentence):
    # Define phrases that indicate the end of a conversation in both English and German
    end_phrases = [
        "stop chat", "exit", "bye", "finish",
        "halt stoppen", "chat beenden", "auf wiedersehen", "tschüss", "ende", "schluss",
    ]
    # Use fuzzy matching to find the closest match to the input sentence and get the match score
    highest_match = process.extractOne(sentence.lower(), end_phrases)
    # Define a threshold for deciding if the sentence means to end the conversation
    threshold = 80  # You can adjust the threshold based on testing
    # Check if the highest match score is above the threshold
    if highest_match[1] >= threshold:
        return True
    else:
        return False

def clean_str_from_markdown(text: str):
    # but first clean the string from newline chars. Add a . to each
    buffer = text.replace('\n', '. ')
    # remove the point we added if there is a mark char before
    buffer = re.sub(r'([?:!.,])\.', r'\1', buffer)
    # insert a space between sentences with no whitespace but a .
    buffer = re.sub(r"(?<!\d)\.(?![\d\s])", ". ", buffer)
    # remove all enumeration fragements (.1. and so on)
    buffer = re.sub(r'\.\d+\.', '.', buffer)
    return buffer

def get_history(state: State):
    """
    Ease of use function to retrieve the history for the current mode
    """
    mode = state[StateKeys.mode.name]
    histories = state[StateKeys.chat_history.name]
    if mode not in histories:
        raise Exception("utils.get_history: Did not find mode in current state.")
    return histories[mode]