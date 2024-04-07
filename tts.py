#!/usr/bin/env python3

"""
Basic example of edge_tts usage.
"""

import asyncio

import edge_tts

from config import VOICE

TEXT = """
    Fashion and Food: A Lean and Healthy Lifestyle

The world of fashion and food is filled with deep-pocketed designers and restaurateurs who create culinary and sartorial experiences that cater to the affluent. However, the recent trend towards health consciousness has led to a shift in the industry. Today, lean is in, and flounces are out.
    """
OUTPUT_FILE = "test.mp3"


async def gen_tts_audio(text: str, filename: str) -> None:
    """Main function"""
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(filename)


if __name__ == "__main__":
    asyncio.run(gen_tts_audio(TEXT, OUTPUT_FILE))
