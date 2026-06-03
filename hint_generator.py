import os
import re
import nltk
import discord
import urllib
import aiohttp
import io

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
    first_sent_tokens = [w for w in word_tokenize(sentences[0]) if w.isalpha() and len(w) > 1]
    first_sent_tags = pos_tag(first_sent_tokens)

    # Scan the whole text for descriptive nouns
    all_tokens = [w for w in word_tokenize(clean_text) if w.isalpha() and len(w) > 1]
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


def get_best_clue(task_text):
    clean_text = re.sub(r'http\S+', '', task_text)
    tokens = word_tokenize(clean_text)
    tagged = pos_tag(tokens)
    sentences = sent_tokenize(clean_text)

    # ignore_list = {'you', 'must', 'have', 'want', 'need', 'task', 'mission', 'participant', 'sas', 'year', 'time',
    #                'day', 'week'}

    ignore_list = {
        'you', 'must', 'have', 'want', 'need', 'task', 'mission',
        'participant', 'sas', 'year', 'time', 'day', 'week', 'secret',
        'agent', 'asai', 'bibler', 'hardy', 'hanifen', 'santa',
        'peggy', 'mom', 'dad', 'david', 'kate', 'kyle', 'jenn', 'tommy',
        'annie', 'justin', 'liz', 'eamonn'}
    generic_nouns = {'someone', 'person', 'thing', 'one', 'place', 'everyone', 'anyone'}

    # --- GENERATE CANDIDATES & EVALUATE STRENGTH ---
    candidates = {}

    # Strategy A: Proper Noun Target
    proper_nouns = [w.upper() for w, t in tagged if t == 'NNP' and w.lower() not in ignore_list]
    if proper_nouns:
        candidates['TARGET'] = (f"TARGET ENTITY: {proper_nouns[0]}", 95)

    # Strategy B: Headcount / Group Scale (NEW 🚀)
    group_indicators = {'everyone', 'everybody', 'all', 'each', 'anybody', 'group', 'sisters', 'players'}
    words_lower = [w.lower() for w in tokens]

    found_headcount = False
    # Check 1: Look for explicit numbers (e.g., "four people", "10 times")
    for i, (word, tag) in enumerate(tagged):
        if tag == 'CD' and i + 1 < len(tagged):
            next_word, next_tag = tagged[i + 1]
            if next_tag.startswith('NN') and next_word.lower() not in {'year', 'time', 'day', 'week'}:
                candidates['HEADCOUNT'] = (f"TARGET SCALE: GROUPS OF {word.upper()} OR MORE", 92)
                found_headcount = True
                break

    # Check 2: Look for blanket group pronouns (e.g., "everyone", "all the sisters")
    if not found_headcount:
        for word in words_lower:
            if word in group_indicators:
                if word in {'everyone', 'everybody', 'all'}:
                    candidates['HEADCOUNT'] = (f"TARGET SCALE: THE ENTIRE ROOM / EVERYONE", 92)
                else:
                    candidates['HEADCOUNT'] = (f"TARGET SCALE: MULTIPLE SPECIFIC TARGETS", 88)
                break

    # Strategy C: Conditional Trigger
    trigger_keywords = {'when', 'whenever', 'if', 'after', 'before', 'while'}
    for kw in trigger_keywords:
        if kw in words_lower:
            idx = words_lower.index(kw)
            phrase = tokens[idx:idx + 3]
            candidates['TRIGGER'] = (f"TRIGGER WARNING: " + " ".join(phrase).upper(), 90)
            break

    # Strategy D: Physical Zone/Location
    spatial_prepositions = {'in', 'at', 'into', 'to', 'inside', 'around', 'on'}
    found_zone = False
    for i, (word, tag) in enumerate(tagged):
        if word.lower() in spatial_prepositions and i + 1 < len(tagged):
            for j in range(i + 1, min(i + 4, len(tagged))):
                next_word, next_tag = tagged[j]
                if next_tag.startswith('NN') and next_word.lower() not in (ignore_list | generic_nouns):
                    candidates['ZONE'] = (f"ZONE ALERT: THE {next_word.upper()}", 85)
                    found_zone = True
                    break
            if found_zone: break

    # Strategy E: Concrete Physical Prop
    abstract_nouns = {'mission', 'year', 'time', 'day', 'week', 'participant', 'sas', 'company', 'content', 'times',
                      'everyone', 'person', 'someone'}
    common_nouns = [w.upper() for w, t in tagged if
                    t.startswith('NN') and w.lower() not in (ignore_list | abstract_nouns | generic_nouns)]
    if common_nouns:
        candidates['PROP'] = (f"PROP DEPLOYMENT: {common_nouns[0]}", 80)

    # Strategy F: Fallback Word-Based Combo
    weak_verbs = {'is', 'are', 'was', 'were', 'be', 'have', 'must', 'do'}
    verb = next((w.upper() for w, t in pos_tag(word_tokenize(sentences[0])) if
                 t.startswith('VB') and w.lower() not in weak_verbs), "OPERATION")
    noun = common_nouns[0] if common_nouns else "OBJECTIVE"
    candidates['WORD_COMBO'] = (f"OPERATION: {verb} {noun}", 60)

    # --- PICK THE WINNER ---
    sorted_candidates = sorted(candidates.items(), key=lambda item: item[1][1], reverse=True)
    return sorted_candidates[0][1][0]


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


import re
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag

# Ensure downloads are ready for the VM
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')


def generate_dynamic_clue(task_text, level=2):
    """
    Generates information-shifting clues with strictly unique words.
    Level 2 = 2 words (Noun 1 + Noun 2) - Zero action context.
    Level 3 = 3 words (Verb + Noun 1 + Noun 2) - Adds the action.
    Level 4 = 4 words (Verb + Noun 1 + Noun 2 + Modifier) - Adds a descriptive detail.
    """
    # 1. Clean out URLs
    clean_text = re.sub(r'http\S+', '', task_text)

    # 2. Setup ignore lists
    ignore_list = {
        'you', 'must', 'have', 'want', 'need', 'task', 'mission',
        'participant', 'sas', 'year', 'time', 'day', 'week', 'secret',
        'agent', 'asai', 'bibler', 'hardy', 'hanifen', 'santa',
        'peggy', 'mom', 'dad', 'david', 'kate', 'kyle', 'jenn', 'tommy',
        'annie', 'justin', 'liz', 'eamonn', 'least', 'ceremony', 'presentation',
        'youve'
    }
    generic_nouns = {'someone', 'person', 'thing', 'one', 'place', 'everyone', 'anyone'}

    # 3. Tokenize and Tag everything
    sentences = sent_tokenize(clean_text)
    if not sentences:
        return "CLASSIFIED OBJECTIVE"

    first_sent_tags = pos_tag(word_tokenize(sentences[0]))
    all_tags = pos_tag(word_tokenize(clean_text))

    # Track used words (in lowercase) to enforce strict uniqueness
    used_words = set()

    # 4. Extract Verb (Action) from the first sentence
    weak_verbs = {'is', 'are', 'was', 'were', 'be', 'been', 'do', 'does', 'did', 'have', 'has', 'had', 'runs'}
    verb = "OPERATION"
    for word, tag in first_sent_tags:
        if tag.startswith('VB') and word.lower() not in weak_verbs and word.lower() not in ignore_list:
            verb = word.upper()
            used_words.add(word.lower())
            used_words.add(word.lower().rstrip('s').rstrip('ing'))
            break

    # 5. Extract Nouns (Targets)
    proper_nouns = [w.upper() for w, t in all_tags if t == 'NNP' and w.lower() not in ignore_list]
    common_nouns = [w.upper() for w, t in all_tags if
                    t.startswith('NN') and w.lower() not in ignore_list and w.lower() not in generic_nouns]

    # Consolidate raw noun list, putting unique Proper Nouns first
    raw_nouns = proper_nouns + [n for n in common_nouns if n not in proper_nouns]

    # Clean and deduplicate nouns against used words and each other
    final_nouns = []
    for noun in raw_nouns:
        noun_lower = noun.lower()
        noun_root = noun_lower.rstrip('s')

        if (noun_lower not in used_words) and (noun_root not in used_words):
            final_nouns.append(noun)
            used_words.add(noun_lower)
            used_words.add(noun_root)

    # Ensure we have at least two unique nouns to work with (fallbacks)
    fallbacks = ["CLASSIFIED", "OBJECTIVE", "TARGET", "SECTOR"]
    for fallback in fallbacks:
        if len(final_nouns) >= 2:
            break
        if fallback.lower() not in used_words:
            final_nouns.append(fallback)
            used_words.add(fallback.lower())

    # 6. Extract Modifiers (Adjectives/Adverbs)
    modifiers = [w.upper() for w, t in all_tags if t.startswith('JJ') or t.startswith('RB')]

    # Find a unique modifier
    modifier = "SPECIFIC"
    for mod in modifiers:
        mod_lower = mod.lower()
        if mod_lower not in ignore_list and mod_lower not in used_words:
            modifier = mod
            break

    # 7. Level Separation Logic
    if level == 2:
        # Cryptic: Just the primary two unique nouns
        return f"{final_nouns[0]} {final_nouns[1]}"

    elif level == 4:
        # Easy: Verb + Noun 1 + Noun 2 + Descriptive Modifier
        return f"{verb} {final_nouns[0]} {final_nouns[1]} {modifier}"

    else:
        # Medium (Level 3): Verb + Noun 1 + Noun 2
        return f"{verb} {final_nouns[0]} {final_nouns[1]}"

async def generate_mission_image(prompt_text: str) -> discord.File:
    """
    Takes a string prompt, fetches an AI-generated image from Pollinations.ai,
    and packages it directly into an in-memory discord.File payload.
    """

    # prompt_text = 'Learn and perform the choreography for Robyn’s “Call your girlfriend” or Beyoncé’s “Single Ladies”.  Record your final performance OR preferably perform it live at the Secret Santa reveal!  Accurate attire encouraged…'

    # 1. Clean and encode the text string to be safe for a URL path
    encoded_prompt = urllib.parse.quote(prompt_text)
    api_key = os.getenv("POLLINATIONS_API_KEY")

    if not api_key:
        print("The api key for pollinations wasn't found!")

    # 2. Build your authorization headers using your account key
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    # 2. Construct the URL (we can attach optional parameters like removing logos or selecting flux)
    api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"


    # 3. Asynchronously fetch the image from the web
    async with aiohttp.ClientSession() as session:
        try:
            # async with session.get(api_url) as response:
            async with session.get(api_url, headers=headers, timeout=45) as response:
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


