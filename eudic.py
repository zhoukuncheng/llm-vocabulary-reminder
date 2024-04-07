import asyncio
import logging
import pprint

import httpx
from async_lru import alru_cache

from config import EUDIC_TOKEN

client = httpx.AsyncClient(timeout=1200)

url = "https://api.frdic.com/api/open/v1/studylist/words/0"
headers = {
    "Authorization": EUDIC_TOKEN
}


@alru_cache(ttl=3600 * 2)
async def list_eudic_glossary(page, page_size=50):
    querystring = {"language": "en", "page": str(page), "page_size": str(page_size)}
    if page_size == 0:
        querystring = {"language": "en"}
    try:
        response = await client.get(url, headers=headers, params=querystring)
        logging.debug(response.headers)
        return response.json()["data"]
    except Exception as e:
        logging.exception(e)
        return ""


def format_glossary(glossary: list[dict]):
    logging.debug(pprint.pformat(glossary))
    return [w["word"] for w in glossary]


if __name__ == '__main__':
    asyncio.run(list_eudic_glossary(page=44))
