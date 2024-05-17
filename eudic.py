import asyncio
import logging
import pprint

import httpx
from async_lru import alru_cache

from config import EUDIC_TOKEN

headers = {
    "User-Agent": "insomnium/0.2.3-a",
    "Authorization": EUDIC_TOKEN,
}


async def add_words_to_eudic(payload: dict) -> dict:
    """
    Asynchronously adds words to the Eudic word list via a POST request.

    Parameters:
        payload (dict): The payload containing words to add.

    Returns:
        dict: The response from the Eudic API.
    """
    url = "https://api.frdic.com/api/open/v1/studylist/words"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()  # Raises an exception for 4XX/5XX errors
            return response.json()  # Directly return the JSON response
    except httpx.RequestError as e:
        logging.error(f"Request error occurred: {e}")
        raise  # Rethrowing the exception for the caller to handle
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error occurred: {e}")
        raise  # Rethrowing the exception for the caller to handle


async def delete_words_from_eudic(payload: dict) -> bool:
    """
    Asynchronously deletes words from the Eudic word list via a DELETE request.

    Parameters:
        payload (dict): The payload containing words to delete.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    url = "https://api.frdic.com/api/open/v1/studylist/words"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.request(
                url=url, method="DELETE", json=payload, headers=headers
            )
            if response.status_code == 204:
                return True
            else:
                logging.error("Failed to delete words: HTTP %s", response.status_code)
                return False
    except httpx.RequestError as e:
        logging.error("Request error occurred: %s", str(e))
        return False
    except Exception as e:
        logging.error("Unexpected error occurred: %s", str(e))
        return False


@alru_cache(ttl=3600 * 1)
async def list_eudic_vocabulary(page, page_size=50):
    querystring = {"language": "en", "page": str(page), "page_size": str(page_size)}
    url = "https://api.frdic.com/api/open/v1/studylist/words/0"

    if page_size == 0:
        querystring = {"language": "en"}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url, headers=headers, params=querystring)
            logging.debug(f"{response.headers=}, {url=}, {querystring=}, {headers=}")
            return response.json()["data"]
    except httpx.RequestError as e:
        logging.error(f"Request error occurred: {e}")
        raise  # Rethrowing the exception for the caller to handle
    except httpx.HTTPStatusError as e:
        logging.error(f"HTTP error occurred: {e}")
        raise  # Rethrowing the exception for the caller to handle
    except Exception as e:
        logging.exception(f"Unexpected error occurred: {e}", exc_info=True)
        raise  # Rethrowing the exception for the caller to handle


def format_words(words: list[dict[str]]):
    for w in words:
        if w.get("exp"):
            w["exp"] = w["exp"].replace("<br>", "\n")
    logging.debug(pprint.pformat(words))
    return [w["word"] for w in words]


if __name__ == "__main__":
    asyncio.run(list_eudic_vocabulary(page=44))
