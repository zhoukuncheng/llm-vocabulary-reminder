# LLM Vocabulary Reminder Bot

English | [中文介绍](https://zhoukuncheng.github.io/posts/llm-vocabulary-reminder/)  

This project is a Telegram bot designed to provide users with daily reminders containing English vocabulary words,
definitions, and example sentences. It utilizes various APIs and libraries to generate engaging and informative content
for language learning and vocabulary building.

## Purpose

The main purpose of this bot is to help users expand their English vocabulary by providing daily exposure to new words
and their usage in context. The bot leverages the power of large language models (LLMs) to create unique and interesting
sentences based on the chosen vocabulary words.

## Features

- Daily Vocabulary Reminders: Receive a set of vocabulary words with definitions and example sentences at scheduled
  times throughout the day.
- LLM-Generated Content: Get unique and creative sentences using the Groq LLM, demonstrating the practical usage of the
  vocabulary words.
- Audio Pronunciation: Listen to the pronunciation of each word using text-to-speech technology.
- Formatted Web Pages: View the generated content in a well-structured format on Telegraph pages.
- Customizable Schedule: Set the specific times you want to receive the reminders.

## Usage

Set Up the Bot: Follow the setup instructions below to configure and deploy the bot.  
Start the Bot: Once deployed, start the bot and use the /set command to schedule your daily reminders.  
Receive Reminders: The bot will send you messages at the scheduled times containing vocabulary words, definitions,
example sentences, and links to audio pronunciations and Telegraph pages.

### Additional Commands:

- `/page [word]`: Get a list of web resources for looking up the definition and usage of a specific word.
- `/audio [word]`: Get the audio pronunciation URL for a specific word.

## Setup

### Clone the Repository:

```bash
git clone https://github.com/zhoukuncheng/llm-vocabulary-reminder.git
```

### Install Dependencies:

```bash
pip install -r requirements.txt
```

### Set Environment Variables:

`TG_BOT_TOKEN`: Your Telegram bot token ([Bot tutorial](https://core.telegram.org/bots/tutorial)).  
`TG_IDS`: Comma-separated list of allowed Telegram user IDs.  
`EUDIC_TOKEN`: Your Eudic API token ([API doc](https://my.eudic.net/OpenAPI/doc_api_study)).   
`GROQ_API_KEY`: Your Groq API key ([API doc](https://console.groq.com/docs/quickstart)).  
`WORDS_SIZE`: Number of vocabulary words to include in each reminder (default: 15).

### Run the Bot:

```bash
python main.py
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests on GitHub.
