import os

from pyhocon import ConfigFactory


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
