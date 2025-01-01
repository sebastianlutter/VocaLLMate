from ollama import Client

from servant.llm.llm_prompt_manager_interface import Mode
from servant.llm.llama_prompt_manager import LlamaPromptManager
from servant.llm.llm_interface import LmmInterface
from servant.llm.llm_prompt_manager_interface import PromptManager, RemoveOldestStrategy


class LmmOllamaRemote(LmmInterface):

    def __init__(self):
        super().__init__()
        self.client = Client(host=self.llm_endpoint)
        self.model = self.llm_provider_model
        self.prompt_manager = LlamaPromptManager(initial_mode=Mode.MODUS_SELECTION,
                                                 reduction_strategy=RemoveOldestStrategy())


    async def chat(self, full_chat):
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