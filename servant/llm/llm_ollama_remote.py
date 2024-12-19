from ollama import Client
from servant.llm.llm_interface import LmmInterface


class LmmOllamaRemote(LmmInterface):

    def __init__(self):
        super().__init__()
        self.client = Client(host=self.llm_endpoint)
        self.model = self.llm_provider_model

    def chat(self, text: str, stream: bool = False):
        if stream:
            return self.chat_stream(text)
        else:
            return self.chat_blocking(text)

    def chat_blocking(self, full_chat):
        content = (
            self.client.chat(
                model=self.model,
                stream=False,
                messages=full_chat,
            )
        )['message']['content']
        return content

    async def chat_stream(self, full_chat):
        content = self.client.chat(
                model=self.model,
                stream=True,
                messages=full_chat,
            )
        #print("KI: ", end='', flush=True)
        for chunk in content:
            c = chunk['message']['content']
            #print(c, end='', flush=True)
            yield c

