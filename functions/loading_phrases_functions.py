import random

#List to choose prhase
loading_phrases = [
    "This might take a moment. Consider it a small pause for your mind.",
    "Good things are forming. No need to rush them.",
    "While you wait, let your thoughts wander a little.",
    "A brief pause: rare, simple, and underrated.",
    "Even progress needs a moment to breathe.",
    "Nothing to do right now and that's perfectly fine.",
    "Take this time as it comes unhurried and yours.",
    "This may take up to a few minutes. A brilliant moment for some coffee. ☕",
    "This may take up to a few minutes. So does your mind to relax"
]

#Function to get a random phrase from the list
def get_random_phrase():
    return random.choice(loading_phrases)
