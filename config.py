import os
from dotenv import load_dotenv

load_dotenv()

# Debug
DEBUG = True

# Discord
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = "!"
_shard_count_raw = os.getenv("SHARD_COUNT")
SHARD_COUNT = int(_shard_count_raw) if _shard_count_raw else None
EMBED_COLOR = 0x7D2D1F
APP_INSTALL_URL = "https://discord.com/oauth2/authorize?client_id=1466870616216047616"

# Scam Detection
MIN_KEYWORDS = 5
OCR_THRESHOLD = 0.6
CHALLENGE_TIMEOUT = 15
SPAM_CHECK_WINDOW = 0.5  # seconds
SPAM_THRESHOLD = 5  # minimum channel-coverage floor for cross-channel spam detection

MOD_CHANNEL_ID = 1471516708551397528
def _parse_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None

# Where `/feedback` posts its embed. Set the env var to override without editing code.
FEEDBACK_CHANNEL_ID = _parse_int_env("FEEDBACK_CHANNEL_ID") or 1498724925328850954
PARDON_ALLOWED_IDS = [
    796341285480300564
] # this is unused i think
PARDON_ALLOWED_ROLE_IDS = [
    1471508733681995809
] # this is unused i think

VERIFY_TIMEOUT_SECONDS = 60
VERIFY_GRACE_SECONDS = 300
RAID_WINDOW_SECONDS = 10
RAID_HIT_THRESHOLD = 2

SCAM_KEYWORDS = [
    "crypto", "casino", "bonus", "register", "claim", 
    "giving", "everyone", "withdraw", "gambling", "bet",
    "reward", "instant", "free", "promo", "code", "robux", "v-bucks", "vbucks"
]

# Random Word API
RANDOM_WORDS = CAPTCHA_WORDS = [
    # Common nouns
    "apple", "banana", "orange", "grape", "lemon", "melon", "peach", "plum",
    "carrot", "potato", "onion", "garlic", "pepper", "tomato", "cucumber",
    "lettuce", "spinach", "broccoli", "cabbage", "celery", "pumpkin", "squash",
    "bread", "butter", "cheese", "milk", "egg", "chicken", "beef", "pork",
    "fish", "shrimp", "lobster", "crab", "oyster", "salmon", "tuna", "cod",
    "rice", "pasta", "noodle", "bean", "lentil", "pea", "corn", "wheat",
    
    # Animals
    "cat", "dog", "bird", "fish", "lion", "tiger", "bear", "wolf", "fox",
    "rabbit", "mouse", "rat", "squirrel", "hedgehog", "penguin", "eagle",
    "owl", "parrot", "duck", "goose", "swan", "cow", "pig", "sheep", "goat",
    "horse", "donkey", "zebra", "giraffe", "elephant", "rhino", "hippo",
    "kangaroo", "koala", "panda", "monkey", "ape", "gorilla", "snake", "frog",
    "turtle", "lizard", "crocodile", "alligator", "spider", "ant", "bee",
    "butterfly", "moth", "beetle", "dragonfly", "worm", "snail", "slug",
    
    # Colors
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
    "black", "white", "gray", "silver", "gold", "cyan", "magenta", "lime",
    "navy", "teal", "maroon", "olive", "coral", "salmon", "khaki", "indigo",
    
    # Body parts
    "head", "arm", "leg", "hand", "foot", "finger", "toe", "eye", "ear",
    "nose", "mouth", "teeth", "tongue", "throat", "chest", "belly", "back",
    "neck", "shoulder", "elbow", "knee", "ankle", "wrist", "hip", "spine",
    
    # Clothing
    "shirt", "pants", "dress", "skirt", "jacket", "coat", "hat", "shoe",
    "sock", "glove", "scarf", "tie", "belt", "button", "zipper", "pocket",
    "sleeve", "collar", "hood", "boot", "sandal", "slipper", "sweater",
    
    # Weather
    "rain", "snow", "cloud", "wind", "storm", "thunder", "lightning", "fog",
    "hail", "sleet", "breeze", "gust", "typhoon", "tornado", "blizzard",
    
    # Objects
    "table", "chair", "desk", "bed", "sofa", "couch", "lamp", "door", "window",
    "wall", "floor", "ceiling", "roof", "fence", "gate", "bridge", "tower",
    "building", "house", "car", "truck", "bus", "train", "plane", "boat",
    "bicycle", "motorcycle", "key", "lock", "box", "bag", "wallet", "phone",
    "laptop", "computer", "keyboard", "mouse", "monitor", "printer", "book",
    "pen", "pencil", "paper", "notebook", "folder", "file", "clock", "watch",
    "cup", "glass", "plate", "bowl", "fork", "spoon", "knife", "pot", "pan",
    
    # Nature
    "tree", "flower", "grass", "leaf", "branch", "root", "seed", "fruit",
    "mountain", "hill", "valley", "river", "lake", "ocean", "beach", "desert",
    "forest", "jungle", "swamp", "canyon", "cave", "volcano", "island", "sky",
    "sun", "moon", "star", "planet", "comet", "asteroid", "galaxy", "nebula",
    
    # Actions/Verbs
    "jump", "run", "walk", "sit", "stand", "fly", "swim", "climb", "crawl",
    "dance", "sing", "laugh", "cry", "smile", "frown", "eat", "drink", "sleep",
    "wake", "work", "play", "read", "write", "draw", "paint", "build", "break",
    "fix", "throw", "catch", "kick", "punch", "push", "pull", "hold", "drop",
    
    # Adjectives
    "big", "small", "tall", "short", "long", "wide", "narrow", "thick", "thin",
    "hot", "cold", "warm", "cool", "fast", "slow", "quick", "soft", "hard",
    "wet", "dry", "clean", "dirty", "bright", "dark", "light", "heavy", "light",
    "loud", "quiet", "sweet", "sour", "bitter", "salty", "spicy", "smooth",
    "rough", "sharp", "dull", "young", "old", "new", "ancient", "modern",
    
    # Emotions
    "happy", "sad", "angry", "calm", "nervous", "brave", "scared", "proud",
    "ashamed", "confused", "curious", "bored", "excited", "tired", "lonely",
    
    # Places
    "park", "school", "hospital", "store", "market", "office", "factory",
    "church", "temple", "mosque", "library", "museum", "theater", "cinema",
    "restaurant", "cafe", "bar", "hotel", "airport", "station", "harbor",
    "port", "farm", "field", "garden", "zoo", "circus", "stadium", "arena",
    
    # Time
    "day", "night", "morning", "evening", "noon", "midnight", "sunrise",
    "sunset", "week", "month", "year", "second", "minute", "hour", "time",
    
    # Miscellaneous
    "number", "letter", "word", "sentence", "sound", "music", "note", "song",
    "dance", "game", "sport", "hobby", "toy", "puzzle", "map", "compass",
    "tool", "machine", "engine", "wheel", "rope", "chain", "wire", "nail",
    "screw", "bolt", "spring", "magnet", "battery", "light", "candle", "match",
    "fire", "water", "air", "earth", "metal", "wood", "plastic", "glass",
    "stone", "brick", "cement", "paint", "ink", "glue", "tape", "rubber",
]
