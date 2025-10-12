import os

from langchain_huggingface import HuggingFacePipeline
from pyhocon import ConfigFactory
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


def get_hf_base_llm(config: ConfigFactory) -> HuggingFacePipeline:
    # Load the tokenizer and model
    model_id = config.get("model_path")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=config["torch_dtype"],
        device_map=config["device_map"],
    )

    # Create a text generation pipeline
    pipeline_args = {
        "model": model,
        "tokenizer": tokenizer,
        "max_new_tokens": config["max_new_tokens"],
        "do_sample": config["do_sample"],
        "pad_token_id": tokenizer.eos_token_id,
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "top_k": config["top_k"],
        "repetition_penalty": config["repetition_penalty"],
    }

    text_generation_pipeline = pipeline(
        "text-generation",
        **pipeline_args,
    )

    # Create a LangChain pipeline
    return HuggingFacePipeline(pipeline=text_generation_pipeline)
