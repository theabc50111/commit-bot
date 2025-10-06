import os
import shlex
import subprocess
import time
from typing import Annotated, Any, Dict, Generator, List, Optional, Tuple

import litellm

from .utils import load_config

THIS_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def count_down(seconds: int) -> None:
    for i in range(seconds, 0, -1):
        print(f"⌛ Waiting for {i:3d} seconds...", end="\r")
        time.sleep(1)
    print(" " * 30, end="\r")  # Clear the line after countdown


class ChunkWrapper:
    _is_thinking = False

    def __init__(self, content: str, reasoning: str, response_metadata: Optional[Dict[str, Any]] = None) -> None:
        self.content = content
        self.reasoning = self._wrap_think_tag(reasoning)
        self.response_metadata = response_metadata

    @classmethod
    def _wrap_think_tag(cls, reasoning: str) -> str:
        output = reasoning
        if reasoning and not cls._is_thinking:
            output = "\n<think>\n" + reasoning
            cls._is_thinking = True
        if not reasoning and cls._is_thinking:
            output = "\n</think>\n\n"
            cls._is_thinking = False
        return output


class ModelExecutor:
    def __init__(self, model_id: str, gen_conf: Dict[str, Any], api_base_url: str, server_type: str) -> None:
        self.model = model_id
        self.gen_conf = gen_conf.copy()
        self.api_base = api_base_url
        self.server_type = server_type
        self._set_vllm_settings()

    def _set_vllm_settings(self) -> None:
        if self.server_type == "vllm":
            self.model = self.model.replace("vllm", "openai")
            self.api_key = "mock_api_key"
            self.warm_up_sec = load_config("job.conf").get("server_warm_up_seconds", 40)
            self.idle_min = load_config("job.conf").get("server_idle_timeout_minutes", 3)
            self.vllm_model_weights_path = load_config("job.conf").get("vllm_model_weights_path", os.path.join(THIS_SCRIPT_DIR, f"model_weights/{self.model.split('/')[-1]}"))

    def _start_vllm_server(self) -> None:
        if self.server_type == "vllm":
            exec_vllm_path = os.path.join(THIS_SCRIPT_DIR, "exec_vllm.sh")
            log_file_path = os.path.join(THIS_SCRIPT_DIR, "var/logs/exec_vllm.log")
            # The expected format for the model id is “vllm/<model name>”, where the model_name corresponds to the parameter we pass to the script.
            model_name = self.model.split("/")[-1]

            start_cmd = f"{exec_vllm_path} --model-path {self.vllm_model_weights_path} --model-name {model_name} --warm-up-sec {self.warm_up_sec} --idle-timeout-min {self.idle_min}"
            command = shlex.split(start_cmd)

            try:
                with open(log_file_path, "a") as log_file:
                    # If vllm server is already running, `exec_vllm.sh` will automatically stop. If not, it will start the server.
                    proc = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)
                    time.sleep(1)  # Give it a moment to stop proc, when vllm server is already running
                if proc.poll() is None:
                    print(
                        f"🗄️ First time starting vllm server for model {model_name}, you don't need to start it again for next {self.idle_min} minutes.(Everytime you send a request, the idle timer will reset.)"
                    )
                    print("🗄️ You can check the logs in exec_vllm.log")
                    print(f"🗄️ Waiting for warm-up..., please wait for about {self.warm_up_sec+5} seconds")
                    count_down(self.warm_up_sec + 5)  # Wait a moment for warm-up of the server
            except FileNotFoundError as e:
                print(f"❌ Error: some file is not found, please check the paths. Details: {e}")
            except Exception as e:
                print(f"❌ An unexpected error occurred while starting the VLLM server: {e}")

    def stream(self, messages: Annotated[List[Dict[str, str]], 'Example: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]']) -> Generator["ChunkWrapper", None, None]:
        self._start_vllm_server()
        params = self.gen_conf
        params["stream"] = True

        response = litellm.completion(model=self.model, messages=messages, **params)

        for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content")
            content = content if content is not None else ""
            reasoning = getattr(delta, "reasoning_content", "")
            model_id = getattr(chunk, "model", "")
            yield ChunkWrapper(content, reasoning=reasoning, response_metadata={"model": model_id})

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ["model", "gen_conf", "server_type", "warm_up_sec", "idle_min", "vllm_model_weights_path"]:
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
        cls._ollama_base_url = conf.get("ollama_base_url")
        cls._vllm_base_url = conf.get("vllm_base_url", None)
        cls._instance = super(AIModels, cls).__new__(cls)
        cls._instance._models = {}
        cls._instance._model_configs = conf.get_config("model_configs").as_plain_ordered_dict()
        cls._instance._default_gen_configs = conf.get_config("default_gen_configs").as_plain_ordered_dict()
        return cls._instance

    def _get_all_configs(self, model_name: str) -> Optional[Tuple[Optional[str], Dict[str, Any]]]:
        model_conf = self._model_configs.get(model_name)
        generate_conf = self._default_gen_configs
        if not model_conf or not generate_conf:
            return None
        return model_conf, generate_conf

    def _create_model(self, model_name: str) -> ModelExecutor:
        configs = self._get_all_configs(model_name)
        if not configs:
            raise UserWarning(f"{model_name} is not in the support list, you can watch it in model.conf")
        model_conf, gen_conf = configs
        model_id, model_server = model_conf["model_id"], model_conf["server_type"]
        if model_server == "ollama":
            self._api_base_url = self._ollama_base_url
        elif model_server == "vllm":
            self._api_base_url = self._vllm_base_url
        else:
            self._api_base_url = None

        return ModelExecutor(model_id, gen_conf, self._api_base_url, model_server)

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
