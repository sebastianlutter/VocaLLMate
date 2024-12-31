from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum

class Mode(Enum):
    EXIT = """
    Wähle EXIT wenn der User das Gespräch beenden will oder sich verabschieded hat.
    """
    GARBAGE_INPUT = """
    Wähle GARBAGE_INPUT wenn die Anfrage unverständlich oder unvollständig erscheint
    """
    LED_CONTROL = """
    Wähle LED_CONTROL wenn der User die Beleuchtung verändern oder eine Farbe haben will
    """
    CHAT = """
    Wähle CHAT wenn der User eine andere bisher nicht genannte Frage gestellt hat.
    """
    MODUS_SELECTION = ''

@dataclass
class PromptTemplate:
    """
    Holds the system prompt and an optional user prompt
    for a particular mode.
    """
    mode: Mode
    system_prompt: str
    user_say_str: str

    def format_prompt(self, context_data: Dict[str, str] = None) -> str:
        if context_data is None:
            context_data = {}
        # Format the system prompt with context data if needed
        system_prompt_formatted = self.system_prompt.format(**context_data)
        return system_prompt_formatted


class PromptManager:

    def __init__(self):
        # Define all your modes and their system prompts here
        self.templates: Dict[str, PromptTemplate] = {
            Mode.MODUS_SELECTION.name: PromptTemplate(
                mode=Mode.MODUS_SELECTION,
                system_prompt=(
                    "Du musst genau einen der folgenden Modi (GROSSBUCHSTABEN) wählen:"
                    f"{', '.join([mode.name for mode in Mode]).replace(Mode.MODUS_SELECTION.name+', ','')}\n"
                    f"Beginne deine Antwort, indem du den gewählten Modus in GROSSBUCHSTABEN nennst (z. B. \"{self.available_modes[0]}\")."
                    "Beende deine Antwort danach. Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text\n"
                    "\nBefolge diese Regeln strikt:\n"
                    "\n".join(f"- {m.value}" for m in Mode if m.value)
                ),
                user_say_str=''
            ),
            "CHAT": PromptTemplate(
                mode=Mode.CHAT,
                system_prompt=(
                    'Beantworte die Fragen als freundlicher und zuvorkommender Helfer.'
                    'Antworte Kindergerecht für Kinder ab acht Jahren.'
                    'Antworte maximal mit 1 bis 3 kurzen Sätzen und stelle Gegenfragen wenn der Sachverhalt unklar ist.'
                ),
                user_say_str='Lass uns etwas plaudern, Modus ist nun CHAT'
            ),
            "LED_CONTROL": PromptTemplate(
                mode_name="LED_CONTROL",
                system_prompt=(
                    "Du steuerst LED-Lichter über eine REST-API. "
                    "Der User möchte sie möglicherweise ein- oder ausschalten oder die Farbe oder Helligkeit ändern."
                    "Parameter und mögliche Werte:"
                    "action: on, off oder invalid wenn User prompt keinen Sinn ergibt."
                    "rgb: Array mit drei Elementen, jeweils von 0 bis 255."
                    "colortemp: Farbtemperatur setzen (2200K bis 6500K)."
                    "brightness: Helligkeit anpassen (Wertebereich 10–255)."
                    "\nStelle sicher, dass deine endgültige Ausgabe ein kurzes JSON-Snippet im folgendem Format ist:\n"
                    "{ 'action': 'on', 'rgb': [255, 0, 0], brightness: 128, 'colortemp': 3000, 'scene': 1}\n"
                    "Beende deine Antwort danach. Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text\n"
                ),
            ),
            "MUSIC_CONTROL": PromptTemplate(
                mode_name="MUSIC_CONTROL",
                system_prompt=(
                    "You can control music playback via REST API. The user might want to "
                    "PLAY, PAUSE, or STOP the music, or change volume."
                ),
            ),
        }

    def get_prompt_template(self, mode: str) -> Optional[PromptTemplate]:
        """
        Retrieve the prompt template for a given mode.
        If mode is invalid, return None or raise an exception.
        """
        return self.templates.get(mode)

    def get_system_prompt(self, mode: str, context_data: Dict[str, str] = None) -> str:
        """
        High-level method: get the prompt template and format it
        with the conversation history and context data.
        """
        template = self.get_prompt_template(mode)
        if not template:
            raise ValueError(f"No prompt template found for mode '{mode}'.")
        return template.format_prompt(context_data)
