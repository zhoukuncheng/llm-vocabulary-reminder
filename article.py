import datetime
import logging

from telegraph.aio import Telegraph


async def write(html: str) -> str:
    telegraph = Telegraph()
    if not telegraph.get_access_token():
        logging.info(await telegraph.create_account(short_name='anonymous'))

    response = await telegraph.create_page(
        f'Glossary - {datetime.datetime.now()}',
        html_content=html,
    )
    logging.info(response)
    return response['url']
