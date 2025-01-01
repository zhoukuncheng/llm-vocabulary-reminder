import asyncio
import logging

from openai import AsyncOpenAI

from config import (
    sys_message_writer,
    OAI_API_KEY,
    OAI_BASE_URL,
    OAI_TEMPERATURE,
    OAI_TOP_P,
    OAI_MAX_TOKENS,
    OAI_MODEL_NAME,
)

oaiClient = AsyncOpenAI(api_key=OAI_API_KEY, base_url=OAI_BASE_URL)


async def gen_chat_completion(sys_prompt: str, prompt: str) -> str:
    logging.debug(
        f"temperature: {OAI_TEMPERATURE}, top_p: {OAI_TOP_P}, model: {OAI_MODEL_NAME}"
    )
    logging.debug(f"user message prompt: {prompt}")
    chat_completion = await oaiClient.chat.completions.create(
        temperature=OAI_TEMPERATURE,
        top_p=OAI_TOP_P,
        messages=[
            {
                "role": "system",
                "content": sys_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        model=OAI_MODEL_NAME,
        max_tokens=OAI_MAX_TOKENS,
    )
    logging.debug(chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content


if __name__ == "__main__":
    txt = asyncio.run(
        gen_chat_completion(
            sys_message_writer,
            "flounce,cost basis,lean,deep-pocketed,qualm,accredited investors,snug",
        )
    )
    print(txt)
