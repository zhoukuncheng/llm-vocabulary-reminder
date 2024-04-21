import datetime
import logging
import re

import httpx
from bs4 import BeautifulSoup
from markdown2 import markdown
from telegraph.aio import Telegraph

client = httpx.AsyncClient(timeout=600)


async def write_to_telegraph(html: str) -> str:
    telegraph = Telegraph()
    if not telegraph.get_access_token():
        logging.info(await telegraph.create_account(short_name="anonymous"))

    response = await telegraph.create_page(
        f"article {datetime.datetime.now(datetime.UTC)}",
        html_content=html,
    )
    logging.info(response)
    return response["url"]


def markdown_to_text(markdown_string):
    """Converts a markdown string to plaintext"""

    # md -> html -> text since BeautifulSoup can extract text cleanly
    html = markdown(markdown_string)

    # remove code snippets
    html = re.sub(r"<pre>(.*?)</pre>", " ", html)
    html = re.sub(r"<code>(.*?)</code >", " ", html)

    # extract text
    soup = BeautifulSoup(html, "html.parser")
    text = "".join(soup.findAll(text=True))

    return text


async def fetch_markdown_from_url(source_url: str) -> str:
    """
    Fetch markdown content asynchronously from a given URL.

    Parameters:
    - source_url (str): The URL to get the markdown for.

    Returns:
    - str: The fetched markdown content.
    """
    r_jina_url = f"https://r.jina.ai/{source_url}"
    response = await client.get(r_jina_url)

    return response.text
