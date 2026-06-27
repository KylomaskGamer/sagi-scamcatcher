import io
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageFile  # <-- Added ImageFile
from deskew import determine_skew
from spellchecker import SpellChecker
import config
import time
import hashlib
import asyncio

# 1. Force Pillow to tolerate slightly incomplete images
ImageFile.LOAD_TRUNCATED_IMAGES = True


def fastcompress(image_bytes: bytes, max_size=(1600, 1600), quality=70):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail(max_size)

        buf = io.BytesIO()
        img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        # If the bytes are completely corrupted, return original bytes and let cv2 handle it
        return image_bytes


class OCRProcessor:
    def __init__(self):
        self.spell = SpellChecker()
        self.spell.word_frequency.load_words(config.SCAM_KEYWORDS)

        self.cache = {}
        self.cache_ttl = 300
        
        # 2. Limit maximum concurrent Tesseract tasks on the machine
        # Adjust '2' based on your server's CPU cores (e.g., 2 or 3 is usually plenty)
        self.semaphore = asyncio.Semaphore(2)

    def _hash(self, image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    def _clean_cache(self):
        now = time.time()
        self.cache = {
            k: v for k, v in self.cache.items()
            if now - v[1] <= self.cache_ttl
        }

    # ---- SYNC CORE (runs in thread) ----
    def _extract_sync(self, image_bytes: bytes) -> str:
        self._clean_cache()

        img_hash = self._hash(image_bytes)

        if img_hash in self.cache:
            text, _ = self.cache[img_hash]
            self.cache[img_hash] = (text, time.time())
            return text

        image_bytes = fastcompress(image_bytes)

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return ""

        angle = determine_skew(img)
        h, w = img.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h), cv2.INTER_CUBIC, cv2.BORDER_REPLICATE)

        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6"
        )

        cleaned_words = []

        for i in range(len(data["text"])):
            word = data["text"][i].strip().lower()
            conf = int(data["conf"][i])

            if conf > 50 and len(word) > 1:
                if word in config.SCAM_KEYWORDS:
                    cleaned_words.append(word)
                else:
                    corrected = self.spell.correction(word)
                    cleaned_words.append(corrected or word)

        text = " ".join(cleaned_words).strip()

        self.cache[img_hash] = (text, time.time())

        return text

    def detect_scam(self, image_bytes: bytes, *, min_keywords: int | None = None) -> bool:
        threshold = int(min_keywords if min_keywords is not None else getattr(config, "MIN_KEYWORDS", 4))
        threshold = max(1, min(50, threshold))

        text = self._extract_sync(image_bytes)
        if not text:
            return False

        lower = text.lower()
        tokens = set(lower.split())
        hit = 0
        for keyword in getattr(config, "SCAM_KEYWORDS", []):
            kw = str(keyword).lower()
            if not kw:
                continue
            if " " in kw:
                if kw in lower:
                    hit += 1
            else:
                if kw in tokens:
                    hit += 1
            if hit >= threshold:
                return True
        return False

    # ---- ASYNC WRAPPER (discord safe with throttle) ----
    async def extract_text(self, image_bytes: bytes) -> str:
        # 3. Queue up tasks here so threads/Tesseract processes don't pile up
        async with self.semaphore:
            return await asyncio.to_thread(self._extract_sync, image_bytes)