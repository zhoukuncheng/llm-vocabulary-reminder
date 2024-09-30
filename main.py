#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.

"""
import asyncio
import datetime
import functools
import logging
import os
import random
import re
import traceback
from typing import Callable, Coroutine
from urllib.parse import quote

import mistune
import pytz
import telegram
import telegramify_markdown
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from article import write_to_telegraph, markdown_to_text, fetch_markdown_from_url
from config import (
    ALLOWED_USER_IDS,
    TG_BOT_TOKEN,
    sys_message_writer,
    CHOSEN_WORDS_SIZE,
    sys_message_explanation,
    MESSAGE_SEND_INTERVAL,
)
from eudic import (
    list_eudic_vocabulary,
    format_words,
    add_words_to_eudic,
    delete_words_from_eudic,
)
from groq_llm import gen_chat_completion
from mdict import query_text_from_mdx
from tts import gen_tts_audio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    level=logging.DEBUG,
)


def allowed_users_only(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine]
) -> Callable:
    """
    Decorator that checks if the user is allowed based on their ID.

    Parameters:
        func (Callable): The original function to be decorated.

    Returns:
        Callable: The wrapped function.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        if user_id not in ALLOWED_USER_IDS:
            logging.error(f"Access denied for user: {update.message.from_user}")
            await update.effective_message.reply_text(
                "You do not have permission to perform this action."
            )
            return

        # User is allowed, call the original function
        return await func(update, context)

    return wrapper


def gen_word_links(i, w, word):
    l = f"""
**{i}. {word}**
{w.get("exp", "")}

{query_text_from_mdx(word)}

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


async def send_telegraph(context, chat_id, text, reply_to_message_id=None):
    try:
        article_url = await write_to_telegraph(
            mistune.create_markdown(
                escape=False,
                hard_wrap=True,
                plugins=["strikethrough", "footnotes", "table", "speedup"],
            )(
                text,
            )
        )
        await context.bot.send_message(
            chat_id, article_url, reply_to_message_id=reply_to_message_id
        )
    except Exception as e:
        logging.exception(e)
        try:
            article_url = await write_to_telegraph(
                mistune.create_markdown(
                    escape=False,
                    hard_wrap=True,
                    plugins=["strikethrough", "footnotes", "table", "speedup"],
                )(
                    telegramify_markdown.convert(text),
                )
            )
            await context.bot.send_message(
                chat_id, article_url, reply_to_message_id=reply_to_message_id
            )
        except Exception as e:
            logging.exception(e)
            await context.bot.send_message(
                chat_id,
                f"{chat_id} failed!:{e}, {traceback.format_exc()}",
            )


async def send_audio(context, job, llm_response, words):
    try:
        audio_filename = f"vocabulary-{datetime.datetime.now(datetime.UTC)}.mp3"
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


def remove_command(text: str) -> str:
    """
    Removes a command at the beginning of the text.

    Parameters:
        text (str): The input text possibly containing a command.

    Returns:
        str: The text with the command removed, if any.
    """
    # Check if the text starts with a '/' and split by space to isolate command
    if text.startswith("/"):
        try:
            _, text_without_command = text.split(" ", 1)
        except ValueError:
            # If split fails (no space found), return an empty string since we only have a command
            return ""
        return text_without_command
    return text


def get_random_subarray_weighted(words: list, subarray_size: int = 15) -> list:
    """
    Selects a random subarray of continuous words of a specified size from a larger
    list of words, with a bias towards the last third of the list.

    Parameters:
    words (list): The list of words from which to select the subarray.
    subarray_size (int): The size of the subarray to select.

    Returns:
    list: A subarray of words of the specified size.
    """
    if subarray_size > len(words):
        return words

    # Calculate the starting index of the last third of the list
    last_third_start_index = len(words) * 2 // 3

    # Decide whether to bias towards the last third or choose from the entire list
    # Let's say we want to bias 70% of the time towards the last third
    if random.random() < 0.7:
        # If biased towards the last third, adjust the start index range accordingly
        if subarray_size <= len(words) - last_third_start_index:
            start_index = random.randint(
                last_third_start_index, len(words) - subarray_size
            )
        else:
            # In case the subarray size is larger than the last third, select from the whole list
            start_index = random.randint(0, len(words) - subarray_size)
    else:
        # If not biased, select from the entire list
        start_index = random.randint(0, len(words) - subarray_size)
    logging.info(
        f"{len(words)=}, {subarray_size=}, {start_index=}, {start_index + subarray_size=}"
    )
    # Extract and return the subarray.
    return words[start_index : start_index + subarray_size]


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    # 获取按钮携带的动态数据
    dynamic_text = query.data
    payload = {"id": "0", "language": "en", "words": [dynamic_text]}
    success = await delete_words_from_eudic(payload)
    # 向用户发送包含动态数据的消息
    if success:
        await query.answer(f"Deleted : {dynamic_text}")
    else:
        await query.answer(f"Delete failed : {dynamic_text}")


async def callback_message(context: telegram.ext.CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    logging.info(context.job)
    # get vocabulary
    vocabulary = await list_eudic_vocabulary(0, 0)
    if not vocabulary:
        await context.bot.send_message(job.chat_id, f"not words")
        return

    # choose words
    k = CHOSEN_WORDS_SIZE

    choice = get_random_subarray_weighted(vocabulary, k)
    words = format_words(choice)
    # send words
    try:
        for i, w in enumerate(choice, 1):
            try:
                word = w.get("word", "").strip()
                l = gen_word_links(i, w, word)
                msg = await context.bot.send_message(
                    job.chat_id,
                    re.sub(r"\n+", "\n", telegramify_markdown.convert(l))[:4096],
                    parse_mode="MarkdownV2",
                )

                # query mdict
                original_exp = query_text_from_mdx(word)
                # llm explain
                llm_explain = await gen_chat_completion(
                    sys_message_explanation,
                    f'word: "{word}", original explanation: \n```{original_exp}```',
                )

                # inline button
                # 创建 InlineKeyboardButton 并设置回调数据
                button = InlineKeyboardButton(text=f"Delete {word}", callback_data=word)
                keyboard = InlineKeyboardMarkup([[button]])

                await context.bot.send_message(
                    job.chat_id,
                    telegramify_markdown.convert(llm_explain),
                    parse_mode="MarkdownV2",
                    reply_to_message_id=msg.message_id,
                    reply_markup=keyboard,
                )
                await asyncio.sleep(MESSAGE_SEND_INTERVAL)

            except Exception as e:
                logging.exception(e)
                await context.bot.send_message(
                    job.chat_id,
                    f"explain {w} failed!:{e}, {traceback.format_exc()}",
                )
                continue

        # llm generate article
        llm_response = await gen_chat_completion(
            sys_message_writer, f"words: \n{words}"
        )

        logging.debug(llm_response)
        # send telegraph
        await send_telegraph(context, job.chat_id, llm_response)
        # gen audio file
        await send_audio(context, job, llm_response, words)

    except Exception as e:
        logging.exception(e)
        await context.bot.send_message(
            job.chat_id, f"{job.name} {job.data} failed!:{e}, {traceback.format_exc()}"
        )


@allowed_users_only
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""

    try:
        for job in context.job_queue.jobs():
            job.schedule_removal()
    except Exception as e:
        logging.error(f"remove all jobs failed: {e}")
    try:
        context.job_queue.run_once(
            callback_message,
            datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai"))
            + datetime.timedelta(seconds=1),
            name="once1",
            chat_id=update.message.chat_id,
        )

        times = [(x, random.randint(15, 55)) for x in range(9, 22)]
        for h, m in times:
            context.job_queue.run_daily(
                callback_message,
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
        await update.effective_message.reply_text(
            audio_url, reply_to_message_id=update.message.message_id
        )
        await gen_tts_audio(text=all_words, filename=audio_filename)
        await update.effective_message.reply_audio(
            audio=audio_filename, reply_to_message_id=update.message.message_id
        )
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
        msg = await update.effective_message.reply_text(
            telegramify_markdown.convert(page_urls),
            parse_mode="MarkdownV2",
            reply_to_message_id=update.message.message_id,
        )
    except (IndexError, ValueError) as e:
        logging.error(e)
        await update.effective_message.reply_text(
            "Please use the /page command followed by a word."
        )
    else:
        # llm explain
        original_exp = query_text_from_mdx(word)
        llm_explain = await gen_chat_completion(
            sys_message_explanation,
            f'word: "{word}, original explanation: \n```{original_exp}```"',
        )
        await update.effective_message.reply_text(
            telegramify_markdown.convert(llm_explain),
            parse_mode="MarkdownV2",
            reply_to_message_id=msg.message_id,
        )


@allowed_users_only
async def add_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get word list from user message
    user_message = remove_command(update.message.text)
    if not user_message:
        await update.message.reply_text("Please provide a list of words to add.")
        return

    # Parsing the input to extract words
    words = [
        word.strip()
        for word in user_message.replace("\n", ",").split(",")
        if word.strip()
    ]

    # Prepare the request payload
    payload = {"id": "0", "language": "en", "words": words}

    try:
        response_json = await add_words_to_eudic(payload)
        message = response_json.get("message", "Words added successfully!")
        await update.message.reply_text(
            message, reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        await update.message.reply_text(
            f"Failed to add words. Please try again later. {e}"
        )
    else:
        # llm explain
        llm_explain = await gen_chat_completion(
            sys_message_explanation, f'explain all these words: "{words}"'
        )
        await send_telegraph(
            context,
            update.message.chat_id,
            llm_explain,
            reply_to_message_id=update.message.message_id,
        )


@allowed_users_only
async def delete_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processes a user message, extracts words, and attempts to delete them from the Eudic word list.
    """

    user_message = remove_command(update.message.text)
    if not user_message:
        await update.message.reply_text("Please provide a list of words to delete.")
        return

    words = [
        word.strip()
        for word in user_message.replace("\n", ",").split(",")
        if word.strip()
    ]

    payload = {"id": "0", "language": "en", "words": words}
    try:
        success = await delete_words_from_eudic(payload)
        if success:
            await update.message.reply_text(
                "Words deleted successfully!",
                reply_to_message_id=update.message.message_id,
            )
        else:
            logging.error(f"An error occurred")
            await update.message.reply_text(
                "Failed to delete words. Please try again later."
            )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        await update.message.reply_text(
            f"Failed to add words. Please try again later. {e}"
        )


@allowed_users_only
async def send_jina_ai_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Processes a user message, extracts words, and attempts to delete them from the Eudic word list.
    """

    source_url = context.args[0]
    if not source_url:
        await update.message.reply_text(f"empty url")
        return
    content = await fetch_markdown_from_url(source_url)
    try:
        # send telegraph
        await send_telegraph(
            context,
            update.message.chat_id,
            content,
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        logging.exception("failed", exc_info=True)
        await update.message.reply_text(
            f"Failed to add words. Please try again later. {e}"
        )


async def query_mdict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        word = " ".join(context.args).strip()
        if not word:
            await update.message.reply_text("Please provide a word to query.")
            return
        definition = query_text_from_mdx(word)
        await update.message.reply_text(
            definition, reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logging.exception("failed", exc_info=True)
        await update.message.reply_text(f"Failed to query mdict. {e}")


@allowed_users_only
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get word list from user message
    user_message = remove_command(update.message.text)
    if not user_message:
        await update.message.reply_text("Please provide input to chat with.")
        return

    try:
        # llm explain
        llm_explain = await gen_chat_completion(
            "You are a helpful assistant. ", f'Answer the question: "{user_message}"'
        )
        await send_telegraph(
            context,
            update.message.chat_id,
            llm_explain,
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        logging.exception("failed", exc_info=True)
        await update.message.reply_text(f"Failed to chat. {e}")


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TG_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("set", set_timer))
    application.add_handler(CommandHandler("define", get_web_definition_url))
    application.add_handler(CommandHandler("audio", get_audio_url))
    application.add_handler(CommandHandler("add", add_words))
    application.add_handler(CommandHandler("remove", delete_words))
    application.add_handler(CommandHandler("jina", send_jina_ai_page))
    application.add_handler(CommandHandler("mdict", query_mdict))
    application.add_handler(CommandHandler("chat", chat))
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
