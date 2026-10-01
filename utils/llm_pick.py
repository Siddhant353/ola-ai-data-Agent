# This file is used to pick the LLM to be used for the agent

import os
from langchain_openai import ChatOpenAI  # import the necessary classes from langchain_openai
from dotenv import load_dotenv           # load environment variables (API keys, model names) from .env
load_dotenv()

# Model names come from .env so the project runs with whatever models your account can use.
# The defaults are the models this project was built and tested with.
MODELS = {
    "low": os.getenv("LLM_LOW", "gpt-5.6-luna"),
    "medium": os.getenv("LLM_MEDIUM", "gpt-5.6-terra"),
    "high": os.getenv("LLM_HIGH", "gpt-5.6-Sol"),
}

def pick_llm(Level: str):
    """
    Picks the appropriate LLM based on the level of the question.

    Args:
        Level (str): Level of the question ("low", "medium" or "high").
    Returns:
        llm (ChatOpenAI): The LLM to be used for the agent.
    """
    model_name = MODELS.get(Level.lower())
    if model_name is None:
        raise ValueError(f"Unsupported level: {Level}")
    return ChatOpenAI(model_name=model_name, temperature=0, reasoning_effort="none")

if __name__ == "__main__":
    llm_obj = pick_llm("low")
    print(llm_obj.invoke("What is the capital of France?"))