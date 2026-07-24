import random

ADJECTIVES = [
    "Introverted", "Adventurous", "Nomadic", "Culinary", 
    "Zen", "Energetic", "Curious", "Mindful", "Spontaneous", 
    "Analytical", "Creative", "Relaxed", "Vibrant"
]

NOUNS = [
    "Hiker", "Explorer", "Foodie", "Backpacker", 
    "Navigator", "Wanderer", "Traveler", "Seeker", 
    "Photographer", "Storyteller", "Observer"
]

def generate_shielded_avatar() -> str:
    """
    Generates a random privacy-shielded avatar name for Zero-Knowledge matching.
    Example: 'The Introverted Hiker'
    """
    return f"The {random.choice(ADJECTIVES)} {random.choice(NOUNS)}"

def generate_avatar_image_url(seed: str) -> str:
    """
    Generates a deterministic abstract avatar image URL based on a seed (like user ID).
    Using an open avatar generation service for abstract shapes.
    """
    return f"https://api.dicebear.com/7.x/identicon/svg?seed={seed}"
