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

def distill_task_sentence(task_text):
    """
    Analyzes a multi-sentence task and returns the single sentence
    that best captures the core objective.
    """
    sentences = sent_tokenize(task_text)

    # If it's already only one sentence, just return it
    if len(sentences) <= 1:
        return task_text.strip()

    sentence_scores = {}

    for index, sentence in enumerate(sentences):
        score = 0
        tokens = word_tokenize(sentence.lower())
        tagged = pos_tag(word_tokenize(sentence))

        # 1. Action weight: Does it start or contain a strong imperative verb?
        # Core game actions (Bring, Hide, Order, Steal) give high value
        weak_verbs = {'is', 'are', 'was', 'were', 'be', 'have', 'must', 'do', 'need', 'want'}
        for word, tag in tagged:
            if tag.startswith('VB') and word.lower() not in weak_verbs:
                score += 15

        # 2. Target weight: Does it mention critical nouns or pronouns?
        # Sentences mentioning "everyone", "sisters", or specific objects are important
        group_indicators = {'everyone', 'everybody', 'all', 'each', 'sisters', 'players', 'participant'}
        for token in tokens:
            if token in group_indicators:
                score += 10

        # 3. Object weight: Number of nouns (more nouns usually means more task details)
        noun_count = len([w for w, t in tagged if t.startswith('NN')])
        score += (noun_count * 2)

        # 4. Position Bias: The first sentence is traditionally the "hook" or summary sentence
        if index == 0:
            score += 20

        # 5. Negative Bias: Sentences dealing with "meta" constraints like links,
        # photo proof, or scheduling add less value to the core summary.
        meta_words = {'submit', 'http', 'picture', 'photo', 'link', 'video', 'proof', 'pool', 'prize'}
        for token in tokens:
            if token in meta_words:
                score -= 25

        sentence_scores[sentence] = score

    # Sort sentences by score and return the highest-ranking one
    sorted_sentences = sorted(sentence_scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_sentences[0][0].strip()


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

    encoded_prompt = "I'm going to share a description for a secret task that someone in my family is trying to " \
                     "accomplish. Generate an image of this task that doesn't give away too many details but is also " \
                     "Christmas themed. Do not generate any text in the image itself.\nThe secret task is: \n" + encoded_prompt

    # 2. Construct the corrected URL targeting the NEW unified endpoint.
    # Note: We pass the key as a URL parameter, along with width, height, and model choice.
    api_url = (
        f"https://gen.pollinations.ai/image/{encoded_prompt}"
        f"?width=1024"
        f"&height=1024"
        f"&nologo=true"
        # f"&model=flux"
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
#                                "The clue should ideally be a pun about about the task or christmas without giving too much away"
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


