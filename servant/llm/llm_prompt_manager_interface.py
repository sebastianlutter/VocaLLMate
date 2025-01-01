from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar, List
from dataclasses import dataclass
from enum import Enum
import tiktoken

# Define Modes
class Mode(Enum):
    EXIT = """
    Wähle EXIT wenn der User das Gespräch beenden will oder sich verabschieded hat.
    """
    GARBAGE_INPUT = """
    Wähle GARBAGE_INPUT wenn die Anfrage unverständlich oder unvollständig erscheint
    """
    LED_CONTROL = """
    Wähle LED_CONTROL wenn der User die Beleuchtung verändern oder eine Farbe haben will.
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

    def format_prompt(self, context_data: Dict[str, str] = None) -> str:
        if context_data is None:
            context_data = {}
        system_prompt_formatted = self.system_prompt.format(**context_data)
        return system_prompt_formatted

# Define type variables for History and Entry
H = TypeVar('H')  # History type
E = TypeVar('E')  # Entry type

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
            print(f"Removed entry to reduce tokens: {removed_entry}")

    def calculate_token_count(self, history: List[Dict[str, str]], tokenize_fn) -> int:
        total_tokens = 0
        for entry in history:
            for key, value in entry.items():
                total_tokens += tokenize_fn(value)
        return total_tokens

# Define PromptManager
class PromptManager(ABC, Generic[H, E]):
    def __init__(self, reduction_strategy: ReductionStrategy):
        self.templates: Dict[str, PromptTemplate] = {
            Mode.MODUS_SELECTION.name: PromptTemplate(
                mode=Mode.MODUS_SELECTION,
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
                system_prompt=(
                    'Beantworte die Fragen als freundlicher und zuvorkommender Helfer. '
                    'Antworte kindergerecht für Kinder ab acht Jahren. '
                    'Antworte maximal mit 1 bis 3 kurzen Sätzen und stelle Gegenfragen, wenn der Sachverhalt unklar ist.'
                ),
                user_say_str='Lass uns etwas plaudern, Modus ist nun CHAT'
            ),
            Mode.LED_CONTROL.name: PromptTemplate(
                mode=Mode.LED_CONTROL,
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
                    "Beende deine Antwort danach. Keine weiteren Erklärungen, Haftungsausschlüsse oder zusätzlicher Text.\n"
                ),
                user_say_str=''
            ),
            Mode.GARBAGE_INPUT.name: PromptTemplate(
                mode=Mode.GARBAGE_INPUT,
                system_prompt=(
                    "Die Benutzereingabe ist unverständlich oder unvollständig. "
                    "Bitte fordere den Benutzer auf, die Anfrage zu präzisieren."
                ),
                user_say_str=''
            ),
            # Add other modes as needed
        }
        self.reduction_strategy = reduction_strategy

    def get_prompt_template(self, mode: str) -> Optional[PromptTemplate]:
        return self.templates.get(mode)

    def get_system_prompt(self, mode: str, context_data: Dict[str, str] = None) -> str:
        template = self.get_prompt_template(mode)
        if not template:
            raise ValueError(f"No prompt template found for mode '{mode}'.")
        return template.format_prompt(context_data)

    @abstractmethod
    def set_history(self, mode: Mode, history: H) -> None:
        pass

    @abstractmethod
    def empty_history(self, mode: Mode) -> None:
        pass

    @abstractmethod
    def get_history(self, mode: Mode) -> H:
        pass

    @abstractmethod
    def get_last_entry(self, mode: Mode) -> Optional[E]:
        pass

    @abstractmethod
    def add_user_entry(self, mode: Mode, user_prompt: str) -> None:
        pass

    @abstractmethod
    def add_ai_entry(self, mode: Mode, ai_response: str) -> None:
        pass

    @abstractmethod
    def count_history_tokens(self, mode: Mode) -> int:
        pass

    @abstractmethod
    def tokenize(self, text: str) -> int:
        pass

    def ensure_token_limit(self, mode: Mode, token_limit: int) -> None:
        current_token_count = self.count_history_tokens(mode)
        if current_token_count > token_limit:
            self.reduction_strategy.reduce(self.histories[mode], self.tokenize, token_limit)
            if self.count_history_tokens(mode) > token_limit:
                print("Warning: Unable to reduce history within the token limit.")

    @abstractmethod
    def reduce_history(self, mode: Mode, token_limit: int) -> None:
        pass


# Concrete Subclass: InMemoryPromptManager
class InMemoryPromptManager(PromptManager[List[Dict[str, str]], Dict[str, str]]):
    def __init__(self, model_name: str = "gpt-3.5-turbo", reduction_strategy: ReductionStrategy = None):
        if reduction_strategy is None:
            reduction_strategy = RemoveOldestStrategy()
        super().__init__(reduction_strategy)
        self.histories: Dict[Mode, List[Dict[str, str]]] = {mode: [] for mode in Mode}
        self.encoder = tiktoken.get_encoding(self.get_encoding_name(model_name))

    def get_encoding_name(self, model_name: str) -> str:
        encoding_map = {
            "gpt-3.5-turbo": "cl100k_base",
            "gpt-4": "cl100k_base",
            # Add other models and their encodings as needed
        }
        return encoding_map.get(model_name, "cl100k_base")

    def set_history(self, mode: Mode, history: List[Dict[str, str]]) -> None:
        if not isinstance(history, list):
            raise TypeError("History must be a list.")
        self.histories[mode] = history

    def empty_history(self, mode: Mode) -> None:
        self.histories[mode].clear()

    def get_history(self, mode: Mode) -> List[Dict[str, str]]:
        return self.histories[mode]

    def get_last_entry(self, mode: Mode) -> Optional[Dict[str, str]]:
        if self.histories[mode]:
            return self.histories[mode][-1]
        return None

    def add_user_entry(self, mode: Mode, user_prompt: str) -> None:
        self.histories[mode].append({'user': user_prompt})

    def add_ai_entry(self, mode: Mode, ai_response: str) -> None:
        self.histories[mode].append({'ai': ai_response})

    def count_history_tokens(self, mode: Mode) -> int:
        total_tokens = 0
        for entry in self.histories[mode]:
            for key, value in entry.items():
                total_tokens += self.tokenize(value)
        return total_tokens

    def tokenize(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def reduce_history(self, mode: Mode, token_limit: int) -> None:
        self.reduction_strategy.reduce(self.histories[mode], self.tokenize, token_limit)

# Example Usage
if __name__ == "__main__":
    # Initialize the prompt manager with default strategy
    prompt_manager = InMemoryPromptManager(model_name="gpt-3.5-turbo")

    # Example usage in CHAT mode
    chat_mode = Mode.CHAT

    # Add multiple user and AI entries
    prompt_manager.add_user_entry(chat_mode, "Hallo, wie geht es dir?")
    prompt_manager.add_ai_entry(chat_mode, "Mir geht es gut, danke! Wie kann ich dir helfen?")
    prompt_manager.add_user_entry(chat_mode, "Kannst du mir ein Gedicht schreiben?")
    prompt_manager.add_ai_entry(chat_mode, "Natürlich! Hier ist ein kurzes Gedicht für dich.")
    prompt_manager.add_user_entry(chat_mode, "Vielen Dank!")

    # Define a token limit
    TOKEN_LIMIT = 20  # Example limit

    # Ensure token limit is not exceeded
    prompt_manager.ensure_token_limit(chat_mode, TOKEN_LIMIT)

    # Retrieve and print history
    chat_history = prompt_manager.get_history(chat_mode)
    print("Chat History after enforcing token limit:", chat_history)
