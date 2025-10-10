import os
import shlex
import subprocess
import time
from typing import Annotated, Any, Dict, Generator, List, Optional, Tuple

import litellm
import requests

from .utils import load_config

THIS_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def count_down(seconds: int, event: str) -> None:
    for i in range(seconds, 0, -1):
        print(f"⌛ {event}..., {i} seconds remaining", end="\r")
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
        self.model_id = model_id
        self.gen_conf = gen_conf.copy()
        self.api_base = api_base_url
        self.server_type = server_type

    def _set_vllm_settings(self) -> None:
        if self.server_type == "vllm":
            log_dir = os.path.join(THIS_SCRIPT_DIR, "var/logs")
            vllm_model_weights_root_dir = load_config("job.conf").get("vllm_model_weights_root_dir", os.path.join(THIS_SCRIPT_DIR, "model_weights"))
            self.model_id = self.model_id.replace("vllm", "openai")
            self.model_name = self.model_id.split("/")[-1]
            self.api_key = "mock_api_key"
            self.warm_up_sec = load_config("job.conf").get("server_warm_up_seconds", 40)
            self.idle_min = load_config("job.conf").get("server_idle_timeout_minutes", 3)
            self.exec_vllm_path = os.path.join(THIS_SCRIPT_DIR, "bin/exec_vllm.sh")
            self.stop_vllm_path = os.path.join(THIS_SCRIPT_DIR, "bin/stop_vllm.sh")
            self.vllm_model_weights_path = os.path.join(vllm_model_weights_root_dir, self.model_name)
            self.exec_vllm_log_path = os.path.join(log_dir, "exec_vllm.log")
            self.stop_vllm_log_path = os.path.join(log_dir, "stop_vllm.log")
            self.vllm_server_log_path = os.path.join(log_dir, "vllm_server.log")

    def _check_model_change_and_stop_previous(self) -> None:
        try:
            res = requests.get(f"{self.gen_conf['api_base']}/models")
        except requests.ConnectionError as e:
            print("🗄️ First time starting the vllm server, no need to check previous model.")
            return
        except Exception as e:
            print(f"❌ An unexpected error occurred while trying to connect to the server. Details:\n{e}")
            return

        if self.server_type != "vllm":
            return
        elif self.server_type == "vllm":
            prev_model = res.json()["data"][0]["id"]

        if prev_model == self.model_name:
            return
        elif prev_model != self.model_name:
            stop_cmd = f"{self.stop_vllm_path}"
            command = shlex.split(stop_cmd)
            try:
                with open(self.stop_vllm_log_path, "w") as log_file:
                    subprocess.run(command, stdout=log_file, stderr=subprocess.STDOUT, check=True)
                time.sleep(1)  # Cool down a bit after stopping the previous server
                print(f"🛑 Stopped the previous vllm server for model: {prev_model}.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to stop the previous vllm server. Error: {e}")
            except Exception as e:
                print(f"❌ An unexpected error occurred while stopping the previous vllm server. Details:\n{e}")

    def _start_vllm_server(self) -> None:
        if self.server_type == "vllm":
            start_cmd = f"{self.exec_vllm_path} --model-path {self.vllm_model_weights_path} --model-name {self.model_name} --warm-up-sec {self.warm_up_sec} --idle-timeout-min {self.idle_min} --server-log-path {self.vllm_server_log_path}"
            command = shlex.split(start_cmd)

            try:
                with open(self.exec_vllm_log_path, "w") as log_file:
                    # If vllm server is already running, `exec_vllm.sh` will automatically stop. If not, it will start the server.
                    proc = subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)
                time.sleep(1)  # Give it a moment to stop proc, when vllm server is already running
                if proc.poll() is None:
                    print(
                        f"🗄️ First time starting vllm server for model {self.model_name}, you don't need to start it again for next {self.idle_min} minutes.(Everytime you send a request, the idle timer will reset.)"
                    )
                    print("🗄️ You can check the logs in exec_vllm.log")
                    print(f"🗄️ Waiting for warm-up..., please wait for about {self.warm_up_sec+5} seconds")
                    count_down(self.warm_up_sec + 5, "Warm-up vllm server")
            except FileNotFoundError as e:
                print(f"❌ Error: some file is not found, please check the paths. Details:\n{e}")
            except Exception as e:
                print(f"❌ An unexpected error occurred while starting the VLLM server. Details:\n{e}")

    def stream(self, messages: Annotated[List[Dict[str, str]], 'Example: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]']) -> Generator["ChunkWrapper", None, None]:
        self._set_vllm_settings()
        self._check_model_change_and_stop_previous()
        self._start_vllm_server()
        params = self.gen_conf
        params["stream"] = True
        response = litellm.completion(model=self.model_id, messages=messages, **params)

        for chunk in response:
            delta = chunk.choices[0].delta
            content = getattr(delta, "content")
            content = content if content is not None else ""
            reasoning = getattr(delta, "reasoning_content", "")
            model_id = getattr(chunk, "model", "")
            yield ChunkWrapper(content, reasoning=reasoning, response_metadata={"model": model_id})

    def __setattr__(self, name: str, value: Any) -> None:
        vllm_settings = ["model_name", "warm_up_sec", "idle_min", "vllm_model_weights_path", "exec_vllm_path", "stop_vllm_path", "exec_vllm_log_path", "stop_vllm_log_path", "vllm_server_log_path"]
        if name in ["model_id", "gen_conf", "server_type"] + vllm_settings:
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

    def _get_all_configs(self, model_spec: str) -> Optional[Tuple[Optional[str], Dict[str, Any]]]:
        model_conf = self._model_configs.get(model_spec)
        generate_conf = self._default_gen_configs
        if not model_conf or not generate_conf:
            return None
        return model_conf, generate_conf

    def _create_model(self, model_spec: str) -> ModelExecutor:
        configs = self._get_all_configs(model_spec)
        if not configs:
            raise UserWarning(f"{model_spec} is not in the support list, you can watch it in model.conf")
        model_conf, gen_conf = configs
        model_id, model_server = model_conf["model_id"], model_conf["server_type"]
        if model_server == "ollama":
            self._api_base_url = self._ollama_base_url
        elif model_server == "vllm":
            self._api_base_url = self._vllm_base_url
        else:
            self._api_base_url = None

        return ModelExecutor(model_id, gen_conf, self._api_base_url, model_server)

    def get_model(self, model_spec: str) -> Optional["ModelExecutor"]:
        if model_spec not in self._models:
            model_instance = self._create_model(model_spec)
            if model_instance:
                self._models[model_spec] = model_instance
            else:
                return None
        return self._models.get(model_spec)

    def list_available_models(self) -> List[str]:
        return list(self._model_configs.keys())
