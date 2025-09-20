import litellm

from .utils import load_config


class ChunkWrapper:
    def __init__(self, content, reasoning):
        self.content = content
        self.reasoning = reasoning


class ModelExecutor:
    def __init__(self, model_name, gen_conf, ollama_base_url=None):
        self.model = model_name
        self.gen_conf = gen_conf
        self.api_base = None
        if "ollama" in self.model:
            self.api_base = ollama_base_url

    def stream(self, messages):
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

    def __setattr__(self, name, value):
        if name in ["model", "gen_conf", "api_base"]:
            super().__setattr__(name, value)
        else:
            self.gen_conf[name] = value


class AIModels:
    _instance = None

    def __new__(cls):
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

    def _get_all_configs(self, model_name: str):
        model_conf = self._model_configs.get(model_name)
        generate_conf = self._default_gen_configs
        if not model_conf or not generate_conf:
            return None
        return model_conf.get("model"), generate_conf

    def _create_model(self, model_name: str):
        model_id, gen_conf = self._get_all_configs(model_name)
        if model_id:
            return ModelExecutor(model_id, gen_conf.copy(), self._ollama_base_url)
        return None

    def get_model(self, model_name: str):
        if model_name not in self._models:
            model_instance = self._create_model(model_name)
            if model_instance:
                self._models[model_name] = model_instance
            else:
                return None
        return self._models.get(model_name)

    def list_available_models(self):
        return list(self._model_configs.keys())
