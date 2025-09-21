import os
import random
import re
from typing import Any

from pyhocon import ConfigFactory

from .prompts import deriv_sys_ppt_1, deriv_sys_ppt_2, deriv_sys_ppt_3


def load_config(config_file_name: str) -> ConfigFactory:
    """
    Load configuration from a HOCON file.
    Args:
        config_file_name (str): Name of the configuration file.
    Returns:
        ConfigFactory: Parsed configuration object.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "conf", config_file_name)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_file_name} not found in {script_dir}/conf")

    return ConfigFactory.parse_file(config_path)


def get_conf_regen_commit_msg() -> tuple[str, dict[str, Any]]:
    new_model_gen_conf = {"temperature": random.uniform(0.3, 0.7)}
    new_sys_ppt = random.choice([deriv_sys_ppt_1, deriv_sys_ppt_2, deriv_sys_ppt_3])

    return new_sys_ppt, new_model_gen_conf


def post_process_commit_message(message: str) -> str:
    """Post-processes the generated commit message to remove unwanted artifacts."""
    # Remove <think>...</think> blocks
    message = re.sub(r"<think>.*?</think>", "", message, flags=re.DOTALL)
    # Remove Body:\n
    message = re.sub(r"Body:\n", "", message)
    # Remove Body:
    message = re.sub(r"Body: ", "", message)
    # Remove <Body>, </Body> tags
    message = re.sub(r"</?Body>", "", message)
    # Remove ``` code blocks and the language specifier
    message = re.sub(r"```[\w]*\n?", "", message)
    # Trim leading/trailing whitespace that might be left after removals
    message = message.strip()
    return message
