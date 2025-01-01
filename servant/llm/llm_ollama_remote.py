from ollama import Client
from servant.llm.llm_interface import LmmInterface


class LmmOllamaRemote(LmmInterface):

    def __init__(self):
        super().__init__()
        self.client = Client(host=self.llm_endpoint)
        self.model = self.llm_provider_model


    async def chat(self, full_chat):
        content = self.client.chat(
                model=self.model,
                stream=True,
                messages=full_chat,
            )
        for chunk in content:
            c = chunk['message']['content']
            yield c

