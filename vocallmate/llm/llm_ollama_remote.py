from ollama import Client

from vocallmate.llm.llm_prompt_manager_interface import Mode
from vocallmate.llm.llama_prompt_manager import LlamaPromptManager
from vocallmate.llm.llm_interface import LmmInterface
from vocallmate.llm.llm_prompt_manager_interface import PromptManager, RemoveOldestStrategy
from typing import Any, Dict, Generic, Optional, TypeVar, List

class LmmOllamaRemote(LmmInterface):

    def __init__(self):
        super().__init__()
        self.client = Client(host=self.llm_endpoint)
        self.model = self.llm_provider_model
        self.prompt_manager = LlamaPromptManager(initial_mode=Mode.MODUS_SELECTION,
                                                 reduction_strategy=RemoveOldestStrategy())

    async def chat(self, full_chat: List[Dict[str, str]]) -> str:
        content = self.client.chat(
                model=self.model,
                stream=True,
                messages=full_chat,
            )
        for chunk in content:
            c = chunk['message']['content']
            yield c

    def get_prompt_manager(self) -> PromptManager:
        return self.prompt_manager
