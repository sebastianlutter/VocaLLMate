import os
import datetime
from abc import ABC, abstractmethod

from servant.llm.llm_prompt_manager_interface import PromptManager


class LmmInterface(ABC):

    def __init__(self):
        self.llm_endpoint=os.getenv('LLM_ENDPOINT', 'http://127.0.0.1:11434')
        self.llm_provider_model=os.getenv('LLM_PROVIDER_MODEL', 'llama3.2:3b')

        self.system_prompt=f"{self.system_prompt}"
    @abstractmethod
    async def chat(self, full_chat):
        pass

    def get_prompt_manager(self) -> PromptManager:
        pass


    def config_str(self):
        return f'model: {self.llm_provider_model}, endpoint: {self.llm_endpoint}'