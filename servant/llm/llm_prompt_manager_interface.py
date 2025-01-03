import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar, List
from dataclasses import dataclass
from enum import Enum
import datetime

# Define Modes
class Mode(Enum):
    EXIT = """
    Wähle EXIT wenn der User das Gespräch beenden oder abbrechen will oder sich verabschieded hat.
    """
    GARBAGEINPUT = """
    Wähle GARBAGEINPUT wenn die Anfrage unverständlich oder unvollständig erscheint
    """
    LEDCONTROL = """
    Wähle LEDCONTROL wenn der User die Beleuchtung verändern oder eine Farbe haben will.
    """
    CHAT = """
    Wähle CHAT wenn der User eine andere bisher nicht genannte Frage gestellt hat.
    """
    MODUS_SELECTION = ''

# Define PromptTemplate
@dataclass
class PromptTemplate:
    mode: Mode
    system_prompt: str
    user_say_str: str
    description: str

    def format_prompt(self, context_data: Dict[str, str] = None) -> str:
        if context_data is None:
            context_data = {}
        system_prompt_formatted = self.system_prompt.format(**context_data)
        return system_prompt_formatted

# Define type variables for History and Entry
H = TypeVar('H')  # History type
E = TypeVar('E')  # Entry type

GLOBAL_BASE_TEMPLATES: Dict[str, PromptTemplate] = {
    Mode.MODUS_SELECTION.name: PromptTemplate(
        mode=Mode.MODUS_SELECTION,
        description='Modus Auswahl',
        system_prompt=(
                "Du musst genau einen der folgenden Modi (GROSSBUCHSTABEN) wählen: "
                f"{', '.join([mode.name for mode in Mode if mode != Mode.MODUS_SELECTION])}\n"
                f"Beginne deine Antwort, indem du den gewählten Modus in GROSSBUCHSTABEN nennst (z. B. \"EXIT\"). "
                "Beende deine Antwort danach. Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text.\n\n"
                "Befolge diese Regeln strikt:\n" +
                "\n".join(f"- {m.value}" for m in Mode if m.value)
        ),
        user_say_str=''
    ),
    Mode.CHAT.name: PromptTemplate(
        mode=Mode.CHAT,
        description='Live Chat Modus',
        system_prompt=(
            'Beantworte die Fragen als freundlicher und zuvorkommender Helfer. '
            'Antworte kindergerecht für Kinder ab acht Jahren. '
            'Antworte maximal mit 1 bis 3 kurzen Sätzen und stelle Gegenfragen, wenn der Sachverhalt unklar ist.'
        ),
        user_say_str='Lass uns etwas plaudern, Modus ist nun CHAT'
    ),
    Mode.LEDCONTROL.name: PromptTemplate(
        mode=Mode.LEDCONTROL,
        description='LED Kontroll Modus',
        system_prompt=(
            "Du steuerst LED-Lichter über eine REST-API. "
            "Der User möchte sie möglicherweise ein- oder ausschalten oder die Farbe oder Helligkeit ändern. "
            "Parameter und mögliche Werte:\n"
            "action: on, off oder invalid wenn User prompt keinen Sinn ergibt.\n"
            "rgb: Array mit drei Elementen, jeweils von 0 bis 255.\n"
            "colortemp: Farbtemperatur setzen (2200K bis 6500K).\n"
            "brightness: Helligkeit anpassen (Wertebereich 10–255).\n"
            "\nStelle sicher, dass deine endgültige Ausgabe ein kurzes JSON-Snippet im folgendem Format ist:\n"
            "{ 'action': 'on', 'rgb': [255, 0, 0], 'brightness': 128, 'colortemp': 3000, 'scene': 1}\n"
            "Der action parameter ist mandatory, andere parameter sind optional."
            "Beende deine Antwort danach. Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text.\n"
        ),
        user_say_str=''
    ),
    Mode.GARBAGEINPUT.name: PromptTemplate(
        mode=Mode.GARBAGEINPUT,
        description='Unverständlicher Input',
        system_prompt=(
            "Die Benutzereingabe ist unverständlich oder unvollständig. "
            "Bitte fordere den Benutzer auf, die Anfrage zu präzisieren."
        ),
        user_say_str=''
    ),
    Mode.EXIT.name: PromptTemplate(
        mode=Mode.EXIT,
        description="Beenden",
        system_prompt='',
        user_say_str=''
    )
}

# Define ReductionStrategy
class ReductionStrategy(ABC):
    @abstractmethod
    def reduce(self, history: List[Dict[str, str]], tokenize_fn, token_limit: int) -> None:
        """
        Reduce the history in-place to fit within the token limit.
        """
        pass

# Concrete Strategy: Remove Oldest Entries
class RemoveOldestStrategy(ReductionStrategy):
    def reduce(self, history: List[Dict[str, str]], tokenize_fn, token_limit: int) -> None:
        """
        Remove the oldest entries until the token count is within the limit.
        """
        while self.calculate_token_count(history, tokenize_fn) > token_limit and history:
            removed_entry = history.pop(0)
            self.logger.debug(f"Removed entry to reduce tokens: {removed_entry}")

    def calculate_token_count(self, history: List[Dict[str, str]], tokenize_fn) -> int:
        total_tokens = 0
        for entry in history:
            content = entry.get("content", "")
            total_tokens += tokenize_fn(content)
        self.logger.debug(f"Calculated total tokens: {total_tokens}")
        return total_tokens

    def __init__(self):
        # Initialize logger for the strategy
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug("RemoveOldestStrategy initialized.")

# Define PromptManager Interface Including Multi-Mode Functions
class PromptManager(ABC, Generic[H, E]):
    """
    Abstract base class for managing prompt histories and interactions with multi-mode support.
    """
    def __init__(self, initial_mode: Mode, reduction_strategy: ReductionStrategy):
        if reduction_strategy is None:
            self.reduction_strategy = RemoveOldestStrategy()
        else:
            self.reduction_strategy = reduction_strategy
        self.current_mode = initial_mode
        self.template = GLOBAL_BASE_TEMPLATES[initial_mode.name]
        # Initialize a history list for each mode
        self.histories: Dict[Mode, List[Dict[str, str]]] = {
            mode: [] for mode in Mode
        }
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"Initialized histories for modes: {[mode.name for mode in self.histories.keys()]}")
        self.logger.debug(f"Initial mode set to {self.current_mode.name}")

    def set_mode(self, mode: Mode) -> None:
        """
        Set the current mode and update the corresponding prompt template.
        """
        if mode not in self.histories:
            self.logger.error(f"Attempted to set unsupported mode: {mode.name}")
            raise ValueError(f"Mode {mode.name} is not supported for history management.")
        self.current_mode = mode
        self.template = GLOBAL_BASE_TEMPLATES[mode.name]
        self.logger.info(f"Mode set to {self.current_mode.name}")

    @abstractmethod
    def set_history(self, history: H) -> None:
        """
        Set the history for the current mode.
        """
        pass

    @abstractmethod
    def empty_history(self) -> None:
        """
        Clear the history for the current mode.
        """
        pass

    @abstractmethod
    def get_history(self) -> H:
        """
        Retrieve the current mode's history.
        """
        pass

    @abstractmethod
    def get_last_entry(self) -> Optional[E]:
        """
        Retrieve the last entry in the current mode's history.
        """
        pass

    @abstractmethod
    def add_user_entry(self, user_prompt: str) -> E:
        """
        Add a user prompt to the current mode's history.
        """
        pass

    @abstractmethod
    def add_assistant_entry(self, ai_response: str) -> E:
        """
        Add an AI response to the current mode's history.
        """
        pass

    @abstractmethod
    def count_history_tokens(self) -> int:
        """
        Count the total number of tokens in the current mode's history.
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Tokenize the input text and return the token count.
        """
        pass

    @abstractmethod
    def reduce_history(self, token_limit: int) -> None:
        """
        Reduce the current mode's history to fit within the token limit.
        """
        pass

    @abstractmethod
    def pretty_print_history(self) -> str:
        pass

    def get_system_prompt(self, context_data: Dict[str, str] = None) -> str:
        """
        Retrieve the formatted system prompt based on the current mode.
        """
        system_prompt = self.template.format_prompt(context_data)
        self.logger.debug(f"System prompt retrieved: {system_prompt}")
        return system_prompt

    def get_timestamp(self) -> str:
        # add the current day, date and time to the prompt
        now = datetime.datetime.now(datetime.timezone.utc)
        # Print in the desired format, e.g., "Es ist Montag, der 30.12.2024 um 13:48 UTC"
        return f"Es ist {now.strftime('%A')}, der {now.strftime('%d.%m.%Y')} um {now.strftime('%H:%M')} UTC. "