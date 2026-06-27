import aiohttp
import random
from config import RANDOM_WORDS

async def get_challenge_word() -> str:
    """Fetch random word from API"""
    try:
        response = random.choices(RANDOM_WORDS, k=1)
        word = str(response[0]).upper()
        return word
    except Exception as e:
        print(f"Error fetching challenge word: {e}")
        return "BONKED"

async def check_embed_images(message, ocr=None) -> bool:
    """Check images in Discord embeds"""
    if not message.embeds:
        return False

    if ocr is None:
        from utils.ocr import OCRProcessor
        ocr = OCRProcessor()

    async with aiohttp.ClientSession() as session:
        for embed in message.embeds:
            if embed.image:
                try:
                    async with session.get(embed.image.url, timeout=5) as response:
                        if response.status != 200:
                            continue
                        image_bytes = await response.read()
                    if ocr.detect_scam(image_bytes):
                        return True
                except Exception as e:
                    print(f"Error checking embed image: {e}")

            if embed.thumbnail:
                try:
                    async with session.get(embed.thumbnail.url, timeout=5) as response:
                        if response.status != 200:
                            continue
                        thumb_bytes = await response.read()
                    if ocr.detect_scam(thumb_bytes):
                        return True
                except Exception as e:
                    print(f"Error checking embed thumbnail: {e}")
    
    return False
