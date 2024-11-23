import os

def LmmFactory():
    provider_name=os.getenv('LLM_PROVIDER')
    match provider_name:
        case 'ollama':
            from servant.llm.llm_ollama_remote import LmmOllamaRemote
            p = LmmOllamaRemote()
            print(f"LlmFactory: start ollama remote provider. {p.config_str()}")
            return p
        case _:
            raise Exception(f"SttFactory: unknown provider name {provider_name}")
