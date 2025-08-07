import os

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


class AIModels:
    def __init__(self):
        self._models = {}
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
        self.model_definitions = {
            "ollama-qwen3:0.6b": lambda: ChatOllama(
                model="qwen3:0.6b",
                streaming=True,
                base_url=ollama_base_url,
            ),
            "ollama-llama3.2:1b": lambda: ChatOllama(
                model="llama3.2:1b",
                streaming=True,
                base_url=ollama_base_url,
            ),
            "openAI": lambda: ChatOpenAI(
                model="gpt-4",
                streaming=True,
                api_key=os.environ.get("OPENAI_API_KEY"),
            ),
            "gemini": lambda: ChatGoogleGenerativeAI(
                model="gemini-pro",
                streaming=True,
                google_api_key=os.environ.get("GOOGLE_API_KEY"),
            ),
            "claude": lambda: ChatAnthropic(
                model="claude-3-opus-20240229",
                streaming=True,
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            ),
        }

    def get_model(self, model_name: str):
        if model_name not in self._models:
            if model_name in self.model_definitions:
                self._models[model_name] = self.model_definitions[model_name]()
            else:
                return None
        return self._models.get(model_name)

    def get_available_models(self):
        return list(self.model_definitions.keys())


if __name__ == "__main__":
    ai_models = AIModels()
    print("Available models:", ai_models.get_available_models())

    # Example for an Ollama model (no API key needed)
    model_name_ollama = "ollama-qwen3:0.6b"
    print(f"Getting model: {model_name_ollama}")
    llm_ollama = ai_models.get_model(model_name_ollama)
    if llm_ollama:
        prompt = "hello, who are you"
        print(f"Streaming response for prompt: {prompt}")
        try:
            for chunk in llm_ollama.stream(prompt):
                print(chunk.content, end="", flush=True)
            print()
        except Exception as e:
            print(f"Error streaming from {model_name_ollama}: {e}")
    else:
        print(f"Model {model_name_ollama} not found.")

    ## Example for OpenAI model (requires OPENAI_API_KEY env var)
    #model_name_openai = "openAI"
    #print(f"Getting model: {model_name_openai}")
    #if os.environ.get("OPENAI_API_KEY"):
    #    llm_openai = ai_models.get_model(model_name_openai)
    #    if llm_openai:
    #        prompt = "hello, who are you"
    #        print(f"Streaming response for prompt: {prompt}")
    #        try:
    #            for chunk in llm_openai.stream(prompt):
    #                print(chunk.content, end="", flush=True)
    #            print()
    #        except Exception as e:
    #            print(f"Error streaming from {model_name_openai}: {e}")
    #    else:
    #        print(f"Model {model_name_openai} not found.")
    #else:
    #    print("Skipping OpenAI test: OPENAI_API_KEY environment variable not set.")
