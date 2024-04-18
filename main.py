#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.

"""
import asyncio
import datetime
import logging
import os
import random
import traceback
from urllib.parse import quote

import mistune
import pytz
import telegram
import telegramify_markdown
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from article import write_to_telegraph, markdown_to_text
from config import (
    ALLOWED_USER_IDS,
    TG_BOT_TOKEN,
    sys_message_writer,
    CHOSEN_WORDS_SIZE,
    sys_message_explanation,
)
from eudic import list_eudic_glossary, format_glossary
from groq_llm import gen_chat_completion
from tts import gen_tts_audio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
)


async def daily_message(context: telegram.ext.CallbackContext) -> None:
    """Send the alarm message."""
    loop = asyncio.get_event_loop()
    job = context.job
    logging.info(context.job)
    # get glossary
    glossary = await list_eudic_glossary(0, 0)
    if not glossary:
        await context.bot.send_message(job.chat_id, f"not glossary")
        return

    # choose words
    k = CHOSEN_WORDS_SIZE

    choice = random.choices(glossary, k=k)
    words = format_glossary(choice)
    # send words
    try:
        for i, w in enumerate(choice, 1):
            word = w.get("word", "").strip()
            l = gen_word_links(i, w, word)
            msg = await context.bot.send_message(
                job.chat_id, telegramify_markdown.convert(l), parse_mode="MarkdownV2"
            )
            if msg:
                # llm explain
                llm_explain = await gen_chat_completion(
                    sys_message_explanation, f'word: "{word}"'
                )
                await context.bot.send_message(
                    job.chat_id,
                    telegramify_markdown.convert(llm_explain),
                    parse_mode="MarkdownV2",
                    reply_to_message_id=msg.message_id,
                )
            await asyncio.sleep(5)

    except Exception as e:
        logging.exception(e)
        await context.bot.send_message(
            job.chat_id, f"{job.name} {job.data} failed!:{e}, {traceback.format_exc()}"
        )

    # llm generate article
    llm_response = await gen_chat_completion(sys_message_writer, f"words: \n{words}")

    logging.debug(llm_response)
    # send telegraph
    await send_telegraph(context, job, llm_response)
    # gen audio file
    await send_audio(context, job, llm_response, words)


def gen_word_links(i, w, word):
    l = f"""
**{i}. {word}**
{w.get("exp", "")}

[🇺🇸 MAmE](https://dict.youdao.com/dictvoice?audio={quote(word)}&type=2)

[🇬🇧  BrE](https://dict.youdao.com/dictvoice?audio={quote(word)}&type=1)

[EUDIC ](https://dict.eudic.net/dicts/en/{quote(word)})

[You Dao ](https://dict.youdao.com/m/result?word={quote(word)}&lang=en)

[Thesaurus ](https://www.thesaurus.com/browse/{quote(word)})

[Google ](https://www.google.com/search?q=define:{quote(word)})

[Merriam Webster ](https://www.merriam-webster.com/dictionary/{quote(word)})

[Vocabulary ](https://www.vocabulary.com/dictionary/{quote(word)})

[Oxford Learner's Dictionary ](https://www.oxfordlearnersdictionaries.com/definition/english/{quote(word.lower())})

[Bing Dict ](https://cn.bing.com/dict/clientsearch?mkt=zh-CN&setLang=zh&form=BDVEHC&ClientVer={quote("BDDTV3.5.1.4320")}&q={quote(word)})

[URBAN DICTIONARY ](https://www.urbandictionary.com/define.php?term={quote(word)})

[Cambridge ](https://dictionary.cambridge.org/dictionary/english/{quote(word)})

"""
    return l


async def send_telegraph(context, job, llm_response):
    try:
        article_url = await write_to_telegraph(
            mistune.create_markdown(
                escape=False,
                hard_wrap=True,
                plugins=["strikethrough", "footnotes", "table", "speedup"],
            )(
                llm_response,
            )
        )
        await context.bot.send_message(job.chat_id, article_url)
    except Exception as e:
        logging.exception(e)
        try:
            article_url = await write_to_telegraph(
                mistune.create_markdown(
                    escape=False,
                    hard_wrap=True,
                    plugins=["strikethrough", "footnotes", "table", "speedup"],
                )(
                    telegramify_markdown.convert(llm_response),
                )
            )
            await context.bot.send_message(job.chat_id, article_url)
        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                job.chat_id,
                f"{job.name} {job.data} failed!:{e}, {traceback.format_exc()}",
            )


async def send_audio(context, job, llm_response, words):
    try:
        audio_filename = f"glossary-{datetime.datetime.now(datetime.UTC)}.mp3"
        await gen_tts_audio(
            text=markdown_to_text(llm_response), filename=audio_filename
        )
        await context.bot.send_audio(
            job.chat_id, audio=audio_filename, caption=f"{", ".join(words)}"
        )
        os.remove(audio_filename)
    except Exception as e:
        await context.bot.send_message(
            job.chat_id,
            f"{job.name} {job.data} audio failed!:{e}, {traceback.format_exc()}",
        )


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    if update.message.from_user.id not in ALLOWED_USER_IDS:
        logging.error(f"banned: {update.message.from_user}")
        await update.effective_message.reply_text(
            f"not allowed: {update.message.from_user}"
        )
        return
    try:
        for job in context.job_queue.jobs():
            job.schedule_removal()
    except Exception as e:
        logging.error(f"remove all jobs failed: {e}")
    try:
        context.job_queue.run_once(
            daily_message,
            datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai"))
            + datetime.timedelta(seconds=1),
            name="once1",
            chat_id=update.message.chat_id,
        )

        times = [(x, random.randint(15, 55)) for x in range(8, 23)]
        for h, m in times:
            context.job_queue.run_daily(
                daily_message,
                datetime.time(hour=h, minute=m, tzinfo=pytz.timezone("Asia/Shanghai")),
                name=f"{h}:{m} job",
                chat_id=update.message.chat_id,
            )

        text = "Timer successfully set!"
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError) as e:
        logging.exception(e)
        await update.effective_message.reply_text(str(e))


# Define the function to handle the /audio command
async def get_audio_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        all_words = " ".join(context.args).strip()
        audio_url = f"https://dict.youdao.com/dictvoice?audio={quote(all_words)}&type=2"
        audio_filename = (
            f"audio-{datetime.datetime.now(datetime.UTC)}-{all_words[:30]}.mp3"
        )
        await update.effective_message.reply_text(audio_url)
        await gen_tts_audio(text=all_words, filename=audio_filename)
        await update.effective_message.reply_audio(audio=audio_filename)
        os.remove(audio_filename)
    except (IndexError, ValueError) as e:
        logging.exception(e)
        await update.effective_message.reply_text(f"IndexError, ValueError: {e}")
    except Exception as e:
        logging.exception(e)
        await update.effective_message.reply_text(
            f"An error occurred. Please try again later: {e}"
        )


# Define the function to handle the /audio command
async def get_web_definition_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        word = " ".join(context.args).strip()
        page_urls = gen_word_links(0, {}, word)
        await update.effective_message.reply_text(
            telegramify_markdown.convert(page_urls), parse_mode="MarkdownV2"
        )
    except (IndexError, ValueError) as e:
        logging.error(e)
        await update.effective_message.reply_text(
            "Please use the /page command followed by a word."
        )


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("set", set_timer))
    application.add_handler(CommandHandler("page", get_web_definition_url))
    application.add_handler(CommandHandler("audio", get_audio_url))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
