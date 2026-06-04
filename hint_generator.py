import os
import re
import nltk
import discord
import urllib
import aiohttp
import io
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag

# import sys
# sys.path.append('/usr/local/lib/python3.14/dist-packages')
# from openai import OpenAI

# Make sure these are downloaded on your cloud VM
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger_eng')


def generate_cryptic_clue(task_text):

    # 1. Strip out URLs so NLTK doesn't get confused by web links
    clean_text = re.sub(r'http\S+', '', task_text)

    # 2. Words to ignore (filler words commonly found in secret tasks)
    ignore_list = {
        'you', 'must', 'have', 'want', 'need', 'task', 'mission',
        'participant', 'sas', 'year', 'time', 'day', 'week', 'secret',
        'agent', 'asai', 'bibler', 'hardy', 'hanifen', 'santa',
        'peggy', 'mom', 'dad', 'david', 'kate', 'kyle', 'jenn', 'tommy',
        'annie', 'justin', 'liz', 'eamonn'
    }

    # 3. Split into sentences and tag parts of speech
    sentences = sent_tokenize(clean_text)
    if not sentences:
        return "OPERATION CLASSIFIED"

    # Focus on the first sentence for the core action verb
    first_sent_tokens = [w for w in word_tokenize(sentences[0]) if w.isalpha() and len(w) > 1 and w != 've']
    first_sent_tags = pos_tag(first_sent_tokens)

    # Scan the whole text for descriptive nouns
    all_tokens = [w for w in word_tokenize(clean_text) if w.isalpha() and len(w) > 1 and w != 've']
    all_tags = pos_tag(all_tokens)

    # 4. Find the best Action (Verb)
    # We skip weak "state of being/possession" verbs like is, are, have, do
    weak_verbs = {'is', 'are', 'was', 'were', 'be', 'been', 'do', 'does', 'did', 'have', 'has', 'had'}
    verb = "OPERATION"
    for word, tag in first_sent_tags:
        if tag.startswith('VB') and word.lower() not in weak_verbs:
            verb = word.upper()
            break

    # 5. Find the best Target (Noun)
    # Priority 1: Proper Nouns (like "Captivate") because they are highly specific
    proper_nouns = [w for w, t in all_tags if t == 'NNP' and w.lower() not in ignore_list]
    # Priority 2: Common Nouns, filtering out generic filler nouns
    generic_nouns = {'someone', 'person', 'thing', 'one', 'place', 'everyone', 'anyone'}
    common_nouns = [w for w, t in all_tags if
                    t.startswith('NN') and w.lower() not in ignore_list and w.lower() not in generic_nouns]

    noun = "CLASSIFIED"
    if proper_nouns:
        noun = proper_nouns[0].upper()
    elif common_nouns:
        noun = common_nouns[0].upper()

    return f"{verb} {noun}"

async def generate_mission_image(prompt_text: str) -> discord.File:
    """
    Takes a string prompt, fetches an AI-generated image from Pollinations.ai,
    and packages it directly into an in-memory discord.File payload.
    """
    api_key = os.getenv("POLLINATIONS_API_KEY")

    if not api_key:
        print("❌ Warning: The api key for pollinations wasn't found in environment variables!")

    # 1. Clean and encode the text string to be safe for a URL path
    encoded_prompt = urllib.parse.quote(prompt_text)

    encoded_prompt = "Generate an cartoonish image of of Santa Claus doing the secret task below." \
                     "The secret task is: \n" + encoded_prompt.strip("\"")

    # 2. Construct the corrected URL targeting the NEW unified endpoint.
    # Note: We pass the key as a URL parameter, along with width, height, and model choice.
    api_url = (
        f"https://gen.pollinations.ai/image/{encoded_prompt}"
        f"?width=1024"
        f"&height=1024"
        f"&nologo=true"
        f"&model=zimage"
        f"&key={api_key}"
    )

    # 3. Asynchronously fetch the image from the web (No 'headers' dict needed!)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, timeout=45) as response:
                if response.status == 200:
                    # Read the binary image data into memory
                    image_bytes = await response.read()

                    # Wrap it in BytesIO so discord.py can read it like a regular file
                    image_file = io.BytesIO(image_bytes)

                    # Return it as a file ready for ctx.send()
                    return discord.File(fp=image_file, filename="mission_visual.png")

                elif response.status == 401:
                    print("❌ Authentication Failed: Your Pollinations API key is invalid or expired.")
                else:
                    error_text = await response.text()
                    print(f"❌ Generation Failed: Server returned status code {response.status}.")
                    print(f"Pollinations Server Error: {error_text}")

        except Exception as e:
            print(f"Image generation exception: {e}")


# ai_client = OpenAI(
#     base_url="https://gen.pollinations.ai/v1",
#     api_key=os.getenv("POLLINATIONS_API_KEY")
# )


# --- Initialize Discord Bot ---
# def generate_ai_clue(task: str):
#     """
#     Generates a two-word clue based on the provided task.
#     Usage: !clue <your task here>
#     """
#     # Let the user know the bot is thinking
#
#     try:
#         # Call the Pollinations AI text API
#         response = ai_client.chat.completions.create(
#             model="openai",  # Adjust model name based on your Pollinations tier/preference
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a helpful game assistant. The user will give you a task. "
#                                "Your job is to generate a relevant clue that is EXACTLY two words long. "
#                                "The clue should be a Christmas pun  about the task without giving too much away"
#                                "Do not include periods, explanations, or introductory text. Just two words."
#                 },
#                 {
#                     "role": "user",
#                     "content": f"Task: {task}"
#                 }
#             ],
#             temperature=0.7
#         )
#
#         # Extract the response text
#         clue = response.choices[0].message.content.strip()
#
#         # Send the result back to Discord
#         print("Generated Clue")
#         return clue
#
#     except Exception as e:
#         print(f"Error calling Pollinations AI in hint generation: {e}")
#         return generate_cryptic_clue(task)


