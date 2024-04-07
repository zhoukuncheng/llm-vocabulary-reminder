#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.

"""
import asyncio
import datetime
import logging
import random
import traceback

import mistune
import pytz
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from article import write
from claude import claude_wrapper
from config import sys_message, ALLOWED_USER_IDS, TG_BOT_TOKEN
from eudic import list_eudic_glossary, format_glossary

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", level=logging.DEBUG
)


async def daily_message(context: telegram.ext.CallbackContext) -> None:
    """Send the alarm message."""
    loop = asyncio.get_event_loop()
    job = context.job
    logging.info(context.job)
    # page_size = 12
    # end = 6500 // page_size
    glossary = await list_eudic_glossary(0, 0)
    if glossary:
        choice = random.choices(glossary, k=12)
        words = format_glossary(choice)

        llm_response = await loop.run_in_executor(None, claude_wrapper.invoke_claude_3_with_text, sys_message,
                                                  f"explain: \n{words}")
        logging.debug(llm_response)
        article = await write(mistune.create_markdown(
            escape=False,
            hard_wrap=True,
            plugins=['strikethrough', 'footnotes', 'table', 'speedup']
        )(llm_response, ))
        try:
            lines = "\n".join([f"{w.get("word")} - {w.get("exp")}" for w in choice])
            await context.bot.send_message(job.chat_id,
                                           f"""
Words:
{lines}


Explain:
{article}

"""
                                           )
        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(job.chat_id, f"send markdown message failed:{e}, {traceback.format_exc()}")


    else:
        await context.bot.send_message(job.chat_id,
                                       text=f"Beep! {job.name} {job.data} failed! \n {traceback.format_exc()}")


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""

    if update.message.from_user.id not in ALLOWED_USER_IDS:
        logging.error(f"banned: {update.message.from_user}")
        await update.effective_message.reply_text(f"not allowed: {update.message.from_user}")
        return
    try:
        for job in context.job_queue.jobs():
            job.schedule_removal()
    except Exception as e:
        logging.error(f"remove all jobs failed: {e}")
    try:
        context.job_queue.run_once(daily_message,
                                   datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai')) + datetime.timedelta(
                                       seconds=1),
                                   name="once1",
                                   chat_id=update.message.chat_id)

        times = [(x, random.randint(10, 20)) for x in range(8, 23)]
        for (h, m) in times:
            context.job_queue.run_daily(daily_message,
                                        datetime.time(hour=h, minute=m, tzinfo=pytz.timezone('Asia/Shanghai')),
                                        name=f"{h}:{m} job",
                                        chat_id=update.message.chat_id)

        text = "Timer successfully set!"
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError) as e:
        logging.exception(e)
        await update.effective_message.reply_text(str(e))


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("set", set_timer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
