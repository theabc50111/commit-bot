from typing import Annotated, Any, Dict, Generator, List, Optional, Tuple

import litellm

from .utils import load_config


class ChunkWrapper:
    _is_thinking = False

    def __init__(self, content: str, reasoning: str) -> None:
        self.content = content
        self.reasoning = self._wrap_think_tag(reasoning)

    @classmethod
    def _wrap_think_tag(cls, reasoning: str) -> str:
        output = reasoning
        if reasoning and not cls._is_thinking:
            output = "\n<think>" + reasoning
            cls._is_thinking = True
        if not reasoning and cls._is_thinking:
            output = "\n</think>\n\n"
            cls._is_thinking = False
        return output


class ModelExecutor:
    def __init__(self, model_name: str, gen_conf: Dict[str, Any], ollama_base_url: Optional[str] = None) -> None:
        self.model = model_name
        self.gen_conf = gen_conf
        self.api_base = None
        if "ollama" in self.model:
            self.api_base = ollama_base_url

    def stream(self, messages: Annotated[List[Dict[str, str]], 'Example: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]']) -> Generator["ChunkWrapper", None, None]:
        params = self.gen_conf.copy()
        if self.api_base:
            params["api_base"] = self.api_base

        response = litellm.completion(model=self.model, messages=messages, **params)

        for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content")
            content = content if content is not None else ""
            reasoning = getattr(delta, "reasoning_content", "")
            yield ChunkWrapper(content, reasoning=reasoning)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["model", "gen_conf", "api_base"]:
            super().__setattr__(name, value)
        else:
            self.gen_conf[name] = value


class AIModels:
    _instance: Optional["AIModels"] = None

    def __new__(cls) -> "AIModels":
        """Singleton pattern to ensure only one instance of AIModels exists."""
        if cls._instance is not None:
            return cls._instance
        conf = load_config("model.conf")
        ollama_base_url = conf.get("ollama_base_url")
        cls._instance = super(AIModels, cls).__new__(cls)
        cls._instance._models = {}
        cls._instance._ollama_base_url = ollama_base_url
        cls._instance._model_configs = conf.get_config("model_configs").as_plain_ordered_dict()
        cls._instance._default_gen_configs = conf.get_config("default_gen_configs").as_plain_ordered_dict()
        return cls._instance

    def _get_all_configs(self, model_name: str) -> Optional[Tuple[Optional[str], Dict[str, Any]]]:
        model_conf = self._model_configs.get(model_name)
        generate_conf = self._default_gen_configs
        if not model_conf or not generate_conf:
            return None
        return model_conf.get("model"), generate_conf

    def _create_model(self, model_name: str) -> Optional["ModelExecutor"]:
        configs = self._get_all_configs(model_name)
        if configs:
            model_id, gen_conf = configs
            if model_id:
                return ModelExecutor(model_id, gen_conf.copy(), self._ollama_base_url)
        return None

    def get_model(self, model_name: str) -> Optional["ModelExecutor"]:
        if model_name not in self._models:
            model_instance = self._create_model(model_name)
            if model_instance:
                self._models[model_name] = model_instance
            else:
                return None
        return self._models.get(model_name)

    def list_available_models(self) -> List[str]:
        return list(self._model_configs.keys())
