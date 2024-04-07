import asyncio
import logging

from groq import AsyncGroq

from config import sys_message_writer, GROQ_API_KEY

client = AsyncGroq(
    api_key=GROQ_API_KEY,
)


async def gen_chat_completion(sys_prompt: str, prompt: str) -> str:
    chat_completion = await client.chat.completions.create(
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
        model="mixtral-8x7b-32768",
        max_tokens=30000,
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
