import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings

logger = logging.getLogger(__name__)


def get_llm(model: str = "gpt-4o", temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=settings.openai_api_key,
    )


async def call_json_llm(system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> dict[str, Any]:
    """Call LLM with JSON mode and return parsed dict. Returns {} on parse failure."""
    llm = ChatOpenAI(
        model=model,
        temperature=0.0,
        openai_api_key=settings.openai_api_key,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    try:
        response = await llm.ainvoke(messages)
        return json.loads(response.content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from LLM: {e}")
        return {}
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise


async def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """Return embedding vector for given text."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(input=text, model=model)
    return response.data[0].embedding
