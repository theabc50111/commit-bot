import os
import random
import re
from pathlib import Path
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
    home_dir = Path.home()
    if (home_dir / f".config/commit-bot/{config_file_name}").exists():
        user_config_path = (home_dir / f".config/commit-bot/{config_file_name}").as_posix()
        user_config = ConfigFactory.parse_file(user_config_path)
    this_script_dir = os.path.dirname(os.path.abspath(__file__))
    module_default_config_path = os.path.join(this_script_dir, "conf", config_file_name)
    module_default_config = ConfigFactory.parse_file(module_default_config_path)
    ret_config = user_config.with_fallback(module_default_config) if "user_config" in locals() else module_default_config

    return ret_config


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
