import discord
from discord.ext import commands
from discord.utils import get
import asyncio
from random import randrange, shuffle
import random
from dotenv import load_dotenv
import os
# import io
# import urllib
import aiohttp
# import pickle
from bot_functions import finalize_route_selection, AgentPollView, confirm_action, generate_cryptic_clue, \
    generate_mission_image, select_task_via_buttons, advance_game, complete_route, count_suspicions, is_the_manager, \
    is_the_agent, is_not_the_agent
from db_manager import hydrate_bot_memory, get_all_pending_tasks, get_all_held_tasks, \
    save_game_to_db, save_player_to_db, save_mission_to_db, delete_mission_from_db, get_all_submitted_tasks, \
    clear_all_database_data
import time

# from hint_generator import generate_ai_clue
from sas_utils import gameState, person, mission
import logging
from discord.ext import tasks
from datetime import datetime, timedelta, date
import asyncio
from db_manager import save_game_to_db

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DB_PATH = os.getenv("DATABASE_FILE", "secret_agent_santa.db") # The second argument is a fallback default

accelerant = 1  # How much you want to speed up timers for debugging

class CheckInManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reveal_checker.start()  # Start the background loop automatically

    def cog_unload(self):
        self.reveal_checker.cancel()

    # Checks once every 5 minutes—incredibly lightweight on performance!
    @tasks.loop(minutes=5)
    async def reveal_checker(self):
        # Wait until the bot memory is fully hydrated out of SQLite on startup
        if not hasattr(self.bot, 'game') or not self.bot.game:
            return

        # Check if a reveal timer is actively running
        target_time = getattr(self.bot.game, 'reveal_timer_at', None)
        if not target_time:
            return

        # Compare the current time against the scheduled database time
        if datetime.now() >= target_time:
            print("⏰ 48 hours elapsed! Initiating suspicion reveal sequence...")

            # Loop over every active player in your family dictionary matrix
            for user_id, player in self.bot.family.items():
                if not getattr(player, 'playing', False):
                    continue

                # Calculate the count dynamically using our helper function
                count = count_suspicions(self.bot, user_id)

                try:
                    # Fetch the User object from Discord to open their private DM channel
                    user = await self.bot.fetch_user(user_id)

                    msg = (
                        f"🕵️ **Mid-Game Intelligence Report** 🕵️\n"
                        f"The 48-hour observation window has closed.\n\n"
                        f"Based on intercepting the team's mid-game check-ins, "
                        f"there are **{count}** other player(s) who actively suspect you are the secret agent."
                    )
                    await user.send(msg)
                except Exception as e:
                    print(f"⚠️ Couldn't DM user {user_id}: {e}")

            # Reset the timer states so it doesn't fire repeatedly
            self.bot.game.reveal_timer_at = None
            await asyncio.to_thread(save_game_to_db, self.bot)
            print("✅ Suspicion notifications completely delivered.")


class SecretAgentBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Type-hinting these as None/Dict explicitly clears the IDE warnings!
        self.game = None
        self.family = {}
        self.missions = {}


# Set up intents (required to read message content)
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

logging.basicConfig(level=logging.INFO)
bot = SecretAgentBot(command_prefix="!", intents=intents)
bot.save_lock = asyncio.Lock()


async def send_orig_channel(ctx, message):
    """Sends a message to the game channel stored in bot"""
    print(f"\tSending a message to the game channel in {ctx.guild} from {ctx.author.name}")
    channel = bot.get_channel(bot.game.game_channel)
    await channel.send(message)


async def check_for_dm(ctx, failure_msg='Oops! Make sure you only message this privately!'):
    """Validates that the message was sent in a dm"""
    if not isinstance(ctx.channel, discord.DMChannel):
        print('Command not in a DM')
        await ctx.send(failure_msg)
        await ctx.author.send("Send the command over here instead!")
        return False
    return True


async def format_task(ident, title='', details='', task_type=''):
    """Formats a task for readout in discord"""
    try:
        print("Printing a task")
        if not bot.missions[int(ident)].task_eligible or bot.missions[int(ident)].hold_for is not None:
            task_type = 'Route'
    except KeyError:
        task_type = ''

    task_type = task_type if task_type != '' else "Task"
    title = title if title != '' else bot.missions[ident].title
    details = details if details != '' else bot.missions[ident].details
    return f" - **{task_type} {ident}: {title}**\n{details}\n\u200B"


async def daily_milestone_checker():
    """Loops every 24 hours to see if it is time to check in on players' feelings"""
    await bot.wait_until_ready()

    while not bot.is_closed():
        # Check the date once every 24 hours
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        if bot.game and getattr(bot.game, 'checkin_date', None) == today_str:
            if not getattr(bot.game, 'checkin_sent', False):
                print(f"[MILESTONE] Today ({today_str}) is the checkpoint day! Triggering check-ins...")

                # Flip the global flag instantly so a bot restart doesn't re-trigger it today
                bot.game.checkin_sent = True
                await asyncio.to_thread(save_game_to_db, bot)

                # Fire off the automated interview task for each player
                for user_id in list(bot.family.keys()):
                    # if bot.family[user_id].playing:
                        # Use create_task so all players get prompted concurrently
                    asyncio.create_task(prompt_user_feeling(user_id))

        # Sleep for 1 day before scanning the calendar again
        await asyncio.sleep(86400)


async def prompt_user_feeling(user_id: int):
    """Reaches out to a user privately with buttons to vote on the secret agent"""
    try:
        user = await bot.fetch_user(user_id)

        # 1. Instantiate our custom button grid view
        poll_view = AgentPollView(bot, user_id)

        if len(poll_view.children) == 0:
            print(f"[POLL] Skipping user {user_id}; not enough eligible players to show choices.")
            return

        # 2. Send the interactive payload down into their DM
        await user.send(
            "👋 **Hey there! Time for your mid-game check-in!**\n"
            "We are officially halfway through our timeline, and things are getting spicy.\n"
            "🕵️ **Who do you think the Secret Agent is?** Choose a player below:",
            view=poll_view
        )

        # 3. Wait for the view system to complete processing a click (or hit its timeout)
        await poll_view.wait()

        # 4. Process the data payload if they made a selection
        if poll_view.chosen_suspect:
            # We save their choice directly into their object structure
            # (Assuming you change .midpoint_feeling to store who they voted for)
            bot.family[user_id].midpoint_feeling = poll_view.chosen_suspect

            await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
            # async with bot.save_lock:
            #     await save_state(bot)

            await user.send(
                "Thank you for locking in your suspicion! Your vote has been securely logged with the manager. 📝")
            print(
                f"[CHECK-IN] Successfully captured suspect selection from user {user_id} -> {poll_view.chosen_suspect}")



        else:
            await user.send("No worries! The poll has closed due to inactivity.")

    except Exception as e:
        print(f"[ERROR] Failed to execute button poll for user {user_id}: {e}")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')

    # Fire the database hydration manager
    hydrate_bot_memory(bot)
    print("🚀 All data arrays successfully synced from SQLite database. Ready to play.")

    # --- RESTART RECOVERY LOGIC ---
    if not bot.family:
        return

    print("Checking for active route deadlines...")
    current_time = time.time()
    day_in_seconds = 86400

    for user_id, player in bot.family.items():
        # Check if they are sitting on held up choices and have a timestamp saved
        print(user_id, bot.family[user_id].hints)
        held_routes = await asyncio.to_thread(get_all_held_tasks, user_id)
        if held_routes and getattr(player, 'route_draw_time', None) is not None:

            # Calculate how many seconds have elapsed since they ran !draw
            seconds_elapsed = current_time - player.route_draw_time

            # Calculate remaining time left on their 24-hour window
            remaining_time = (day_in_seconds - seconds_elapsed)

            # Inner worker function for the recovered loop
            async def recovered_countdown(uid, delay):
                if delay > 0:
                    print(f" -> Restoring countdown for user {uid}. "
                          f"{round(delay / 3600, 2)} hours remaining.")
                    await asyncio.sleep(delay)
                else:
                    print(f" -> User {uid} deadline expired while the bot was offline!")

                # Double-check if they still need auto-assigning when the timer lands
                held = await asyncio.to_thread(get_all_held_tasks, user_id)
                if uid in bot.family and held:
                    await finalize_route_selection(bot, None, uid, chosen_route_id=None)

            # Spin up the recovered background task
            asyncio.create_task(recovered_countdown(user_id, remaining_time))

    print("Deadline checks complete. Bot is ready to roll.")

    bot.loop.create_task(daily_milestone_checker())
    print(f"Daily milestone scheduler loop has been initialized to check "
          f"at {'~' if bot.game is None else bot.game.checkin_date}.")

    bot.loop.create_task(paranoia_engine_loop())
    print("Paranoia Engine scheduler loop has been initialized.")

    if bot.game is not None:
        print(f"Activated game in {bot.game.status} status with {len(bot.family)} "
              f"players {[bot.family[k].name for k in bot.family]}")


async def paranoia_engine_loop():
    """Background task loop that occasionally triggers automated suspicions"""
    await bot.wait_until_ready()

    while not bot.is_closed():
        # 1. Wait a random interval between 4 and 8 hours
        # (4 hours = 14400s, 8 hours = 28800s)
        # Tip: For testing, change this to random.randint(30, 60) for seconds!
        wait_time = random.randint(60*60*24*10, 60*60*24*31)
        await asyncio.sleep(wait_time)

        # 2. Check if a game is actively running with players
        if not bot.game or not bot.family:
            continue

        # Compile lists of playing candidates
        playing_ids = [uid for uid, p in bot.family.items() if p.playing]
        if len(playing_ids) < 2:  # Need at least 2 players to cross-reference
            continue

        # 3. Pick a random target to talk about
        suspect_id = random.choice(playing_ids)
        suspect_name = bot.family[suspect_id].name

        # 4. Flip a coin: 50% chance Public Channel, 50% chance Private DM
        trigger_type = random.choice(["public", "private"])

        suspicious_phrases = [
            f"Have you seen **{suspect_name}** lately? That's pretty sketch...",
            f"Is it just me, or has **{suspect_name}** been acting a bit too quiet?",
            f"Keep your eyes on **{suspect_name}**. Something doesn't add up.",
            f"A little bird told me **{suspect_name}** might be covering their tracks...",
            f"**{suspect_name}** has been asking to \"!view tasks\" a lot. Where are they right now?"
        ]
        chosen_message = random.choice(suspicious_phrases)

        if trigger_type == "public":
            # Send to the primary game channel
            try:
                channel = bot.get_channel(bot.game.game_channel)
                if channel:
                    async with channel.typing():
                        await asyncio.sleep(2)  # Add a tiny realistic delay
                        await channel.send(f"👀 {chosen_message}")
                        print(f"[PARANOIA] Sent public suspicion about {suspect_name}")
            except Exception as e:
                print(f"[ERROR] Paranoia Engine public fail: {e}")

        elif trigger_type == "private":
            # Select a random player who ISN'T the suspect to receive the whisper
            recipient_pool = [uid for uid in playing_ids if uid != suspect_id]
            if recipient_pool:
                recipient_id = random.choice(recipient_pool)
                try:
                    user = bot.get_user(recipient_id)
                    await user.send(f"🕵️ *Psst...* {chosen_message}")
                    print(f"[PARANOIA] Whispered a suspicion about {suspect_name} to player ID {recipient_id}")
                except Exception as e:
                    print(f"[ERROR] Paranoia Engine private DM fail for user {recipient_id}: {e}")


@bot.command()
@commands.has_role("sas_manager")
async def start(ctx, expected_size=None):
    """Starts a game of secret agent santa"""

    if expected_size is None:
        channel = ctx.guild.get_channel(ctx.channel)
        print(channel)
        expected_size = len(ctx.channel.members)-1  # Ignore the sas_bot

    role = get(ctx.guild.roles, name="sas_manager")
    if role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    if len(bot.family) > 0 or len(bot.missions) > 0 or bot.game is not None:
        await ctx.send("Your game files aren't empty. You sure you want to delete them and start from scratch?")
        try:
            go_ahead = await bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Aborting. A 'YES' would have let you proceed")
        if go_ahead.content != "YES":
            await ctx.send("Aborting. A 'YES' would have let you proceed")
            return 0

        # This is where the deletion happens
        await asyncio.to_thread(clear_all_database_data)

    await ctx.send("Hi there. I'll start a game in this channel. I'm expecting %s players" % expected_size)
    print("Game Channel ID: ", ctx.channel.id)
    bot.family = {}
    bot.missions = {}

    game_channel = ctx.channel.id
    expected_size = int(expected_size)
    bot.game = gameState("Joining", expected_size, 0, game_channel)

    # 🆕 --- AUTOMATIC MIDPOINT CALCULATION ---
    today = date.today()
    end_of_year = date(today.year, 12, 31)

    # Calculate total days between now and Dec 31st, then find the half-way point
    days_remaining = (end_of_year - today).days
    midpoint_delta = timedelta(days=days_remaining // 2)
    calculated_midpoint = today + midpoint_delta

    # Store it as a clean text string variable in pkl
    bot.game.checkin_date = calculated_midpoint.strftime("%Y-%m-%d")
    bot.game.checkin_sent = False
    # ------------------------------------------
    await asyncio.to_thread(save_game_to_db, bot)
    await ctx.send(
        "♻️ **Game Reset Successful!** RAM variables cleared and SQLite database tracking tables purged.")
    print(f"Starting Game. Check-in milestone auto-set for: {bot.game.checkin_date}")
    print("Starting Game in:", ctx.channel, " with %i players" % expected_size)

    await ctx.send("The game's started. Everyone can start joining with !join")


@bot.command()
@commands.check(lambda x: bot.game.status == "Joining")
async def join(ctx):
    """Use to join the active game"""

    if ctx.author.id in bot.family:
        return await ctx.author.send("You're already in the game, %s" % bot.family[ctx.author.id].name)

    await ctx.send("Welcome to the game, %s! \n I'll send you a message for more details" % ctx.author.name)
    await ctx.author.send("Hey there! Welcome to our private channel. This is where you'll interact with me")
    await ctx.author.send("First off, what should I call you?")

    def check(m):
        # return m.author == ctx.author and m.channel == ctx.author
        return m.author.id == ctx.author.id and m.guild is None

    name_good = False
    name = None
    partner = None
    playing = None
    while not name_good:
        try:
            name = await bot.wait_for('message', check=check, timeout=30)
            name_good = await confirm_action(ctx, f"Your name is {name.content}, right?")
            # await ctx.author.send("I'm going to call you %s. Reply 'yes' to confirm" % name.content)
            # ng = await bot.wait_for('message', check=check, timeout=30)
            # name_good = ng.content.lower() == 'yes'
        except asyncio.TimeoutError:
            return await ctx.author.send("You took too long to respond! Try again!")
        if not name_good:
            await ctx.author.send("Okay, what should I call you instead?")

    await ctx.author.send("Amazing, %s. Next, who is your partner?" % name.content +
                          "\n(They're the person we won't pair you with for gifts)")
    part_good = False
    while not part_good:
        try:
            partner = await bot.wait_for('message', check=check, timeout=30)
            part_good = await confirm_action(ctx, f"Your partner is named {partner.content}, right?")
            # await ctx.author.send("Your partner is named %s? Reply 'yes' to confirm" % partner.content)
            # pg = await bot.wait_for('message', check=check, timeout=30)
            # part_good = pg.content.lower() == 'yes'
        except asyncio.TimeoutError:
            return await ctx.author.send('Sorry, you took too long! Try again with "!join"')

        if not part_good:
            await ctx.author.send("Let's try again. What is your partner's name?")

    await ctx.author.send("Sweet. One last question:")

    play_good = False
    while not play_good:
        play_good = await confirm_action(ctx, "You're playing the game this year, right!?")
        if not play_good:
            play_good = await confirm_action(ctx, "Bummer. You're absolutely sure?!")
            playing = not play_good
        elif play_good:
            playing = True
            await ctx.author.send("Great! Next, you can add your tasks by messaging me !add task")

    bot.family[ctx.author.id] = person(name.content, str(ctx.author.name), str(partner.content), playing)
    # Clean, one-line database save directly inside a command handler!
    await asyncio.to_thread(save_player_to_db, ctx.author.id, bot.family[ctx.author.id])
    # async with bot.save_lock:
    #     await save_state(bot)

    print(name.content, "is in!")
    foo = ''
    if not playing:
        foo = " (But they aren't playing)"
    await send_orig_channel(ctx, "%s is registered!%s" % (name.content, foo))

    if len(bot.family) == bot.game.expected_players:
        # All the Family Members are in
        print(f"All {len(bot.family)} players are in")
        await send_orig_channel(ctx, "It looks like everyone is in! Make sure you all submit tasks...")


@bot.command()
@commands.dm_only()
async def add(ctx, task_type=''):
    """Submit a task or a route card"""

    if ctx.author.id not in bot.family:
        return await ctx.send("You haven't registered! Use !join to get in the game")

    # --- DEADLINE ENFORCEMENT ---
    if bot.game and getattr(bot.game, 'submission_deadline', None):
        try:
            # Parse the text string variable back into a date object
            deadline_date = datetime.strptime(bot.game.submission_deadline, "%Y-%m-%d").date()
            current_date = datetime.now().date()

            # If today's date has passed the deadline
            if current_date > deadline_date:
                formatted_deadline = deadline_date.strftime("%B %d, %Y")
                return await ctx.author.send(
                    f"⛔ **Submissions Closed!** The deadline to add routes was **{formatted_deadline}**. "
                    "You cannot add any more tasks at this stage."
                )
        except ValueError:
            print(f"[ERROR] Invalid format inside bot.game.submission_deadline: {bot.game.submission_deadline}")
    # -------------------------------

    def check(m):
        return(
            m.author.id == ctx.author.id  # Must be the same user
            and isinstance(m.channel, discord.DMChannel)  # Must be in DMs
        )

    if task_type.lower() not in ['task', 'route']:
        if bot.game.status == 'Joining' and bot.family[ctx.author.id].playing:
            task_type = 'task'
        else:
            task_type = 'route'

        msg = "I'm not sure what kind of mission you want to add. Next time, use !add task/route\n" \
              "Should I assume you want to add a %s? (yes/no)" % task_type
        type_confirm = await confirm_action(ctx, confirm_message=msg)
        if not type_confirm:
            return await ctx.send("Okay. Let's just start over. Give me another command whenever you're ready")

    if not bot.family[ctx.author.id].playing and task_type.lower() != 'route':
        return await ctx.send("You're not playing, so you don't need to add tasks! You can add routes, though")
    user_id = int(ctx.author.id)
    if len([k for k in bot.family[user_id].submissions if bot.missions[k].task_eligible]) == 3 and task_type == 'task':
        return await ctx.send("Hey %s! You submitted three tasks already." % bot.family[ctx.author.id].name +
                              '\nYou can see them with "!view submissions".')

    # 1. Ask the user for the task
    await ctx.send("Let's get it started. Give me a title for the task")
    # 2. Define a check to make sure the bot listens to the right person and channel

    try:
        # 3. Wait for the user's next message (timeout after 30 seconds)
        msg = await bot.wait_for('message', check=check, timeout=90.0)
        await ctx.author.send("Cool. Now give me the details!")
        det = await bot.wait_for('message', check=check, timeout=90.0)
    except asyncio.TimeoutError:
        return await ctx.author.send("Sorry, you took too long to reply!")

    # 4. Copy the message into a response

    task_id = randrange(1, 1000)
    while task_id in bot.missions:
        task_id = randrange(1, 1000)

    is_task = False
    is_route = False
    if task_type == 'task':
        is_task = True
        is_route = await confirm_action(ctx, "This is a main task. Should I also include it as a route card?")
    elif task_type == 'route':
        is_route = True

    new_task = mission(str(msg.content), str(det.content), ctx.author.id,
                       task_eligible=is_task, route_eligible=is_route)

    try:
        await ctx.author.send(await format_task(task_id, new_task.title, new_task.details))
        submit_check = await confirm_action(ctx, f"You're good to submit this {task_type}?")
        if submit_check:
            await ctx.author.send("Cool. I'll add it!")
            # bot.missions[new_task.ident] = new_task
            # bot.family[ctx.author.id].submissions.append(new_task.ident)
        else:
            return await ctx.author.send("Consider it forgotten")
    except asyncio.TimeoutError:
        return await ctx.author.send("Sorry, you took too long to reply!")

    bot.missions[task_id] = new_task
    bot.family[user_id].submissions.append(task_id)
    print("Save State in !add")
    print("TaskID in !add save:", task_id, new_task, len(bot.missions))
    await asyncio.to_thread(save_mission_to_db, task_id, bot.missions[task_id])
    # async with bot.save_lock:
    #     await save_state(bot)

    ready_to_go = True
    for k in bot.family:
        # print(bot.family[k].name, len(bot.family[k].submissions), bot.family[k].playing)
        task_submits = [t for t in bot.family[t] if bot.missions[t].tesk_eigible]
        if (len(task_submits) < 3 and bot.family[k].playing) or \
                len(bot.family) != bot.game.expected_players:
            print("!add run by %s. Someone still isn't done" % bot.family[ctx.author.id].name)
            ready_to_go = False
            break
    if ready_to_go and task_type != 'route':
        print("Everyone is in. Send Message")
        await send_orig_channel(ctx, "Looks like everyone has three tasks in! Let's go!!!")


@bot.command()
@commands.dm_only()
async def view(ctx, view_what=''):
    """View submissions/selections/tasks/routes/hints"""

    user_id = ctx.author.id

    # Clean up the view_what variable as a default, then confirm with user
    if view_what.lower() not in ['submissions', 'selections', 'tasks', 'task', 'routes',
                                 'pending routes', 'hints', 'hint']:
        if bot.game.status == 'Selecting':
            view_what = 'selections'
        elif bot.game.status == 'Playing':
            view_what = 'tasks'
        elif bot.game.status == "Joining":
            view_what = 'hints'
        else:
            view_what = 'submissions'

        msg = "I'm not sure what you want to see. Instead, use !view submissions/selections/tasks/routes/hints \n" \
              "Do you want to see your %s?" % view_what
        type_confirm = await confirm_action(ctx, msg)
        if not type_confirm:
            return await ctx.author.send("Never mind...")

    # Based on view_what, determine what to view
    to_view = bot.family[user_id].submissions
    if view_what == 'selections':
        to_view = bot.family[user_id].selections
    elif view_what == 'tasks' or view_what == 'task':
        to_view = bot.family[user_id].tasks
    elif view_what == 'routes' or view_what == 'held routes':
        view_what = 'held routes'
        to_view = await asyncio.to_thread(get_all_held_tasks, ctx.author.id)
    elif view_what == 'hints' or view_what == 'hint':
        view_what = 'hints'
        if bot.game.status == "Joining":  # Hints need to be generated for the submissions
            to_view = [k for k in bot.family[ctx.author.id].submissions if bot.missions[k].task_eligible]
        else:
            to_view = bot.family[ctx.author.id].hints

    # Let the user select which task/route/hint to view
    if view_what != "hints":
        await ctx.author.send("You have %i %s for this game" % (len(to_view), view_what))
    else:
        await ctx.author.send("You have %i tasks with %s for this game" % (len(to_view), view_what))

    hide_titles = view_what == "hints"
    task_id = await select_task_via_buttons(bot, ctx, "Choose one to view!",
                                            list(to_view), include_exit=True, hide_titles=hide_titles)
    # Catch abort condition
    if task_id is None:
        print(f"User {user_id} aborted !view command")
        return

    # Actually show the user what they asked for
    if view_what != 'hints':
        await ctx.author.send(await format_task(task_id))
        if view_what == 'submissions':
            route_confirm = "is" if bot.missions[task_id].route_eligible else "is __not__"
            await ctx.author.send(f"This task {route_confirm} eligible to be  a route card")
    elif bot.game.status != 'Joining':  # You have to generate hints from the lookup
        print("Hint ID in !view (not joining):", task_id, type(task_id))
        title = bot.missions[task_id].title if to_view[task_id].get(0, False) else "__<TITLE REDACTED>__"
        details = generate_cryptic_clue(bot.missions[task_id].details) if to_view[task_id].get(1, False) else "__HINT REDACTED__"
        # details = generate_ai_clue(bot.missions[task_id].details) if to_view[task_id].get(1, False) else "__HINT REDACTED__"
        f = await generate_mission_image(bot.missions[task_id].details) if to_view[task_id].get(2, False) else None
        await ctx.author.send(await format_task(task_id, title=title, details=details), file=f)
    else:  # You have to generate hints from the submissions
        print("Hint ID in !view (joining):", task_id, type(task_id), len(to_view))
        title = bot.missions[task_id].title
        details = generate_cryptic_clue(bot.missions[task_id].details)
        # details = generate_ai_clue(bot.missions[task_id].details)
        f = await generate_mission_image(bot.missions[task_id].details)
        msg = await format_task(task_id, title=title, details=details)
        await ctx.author.send(msg, file=f)


@bot.command()
@commands.dm_only()
async def clear(ctx, task_id=None):
    """Clear a task that you've submitted"""

    if bot.game.status != "Joining":
        return await ctx.author.send("Sorry, this task only works for submissions earlier in the game")
    if task_id is None:
        task_id = await select_task_via_buttons(bot, ctx, "Choose a task to clear!",
                                          bot.family[ctx.author.id].submissions, include_exit=True)
        if task_id is None:
            return await ctx.author.send("No worries. I'll leave everything as is")

    task_id = int(task_id)
    await ctx.author.send(await format_task(task_id))
    chk = await confirm_action(ctx, f"You want me to delete task {task_id}?")

    if chk:
        del bot.missions[task_id]
        # bot.family[ctx.author.id].submissions = [k for k in bot.family[ctx.author.id].submissions if k != task_id]
        await asyncio.to_thread(delete_mission_from_db, task_id)
        bot.family[ctx.author.id].submissions.remove(task_id)
        # async with bot.save_lock:
        #     await save_state(bot)
        await ctx.author.send("I've deleted task %i" % task_id)
    else:
        await ctx.author.send("Alright, I'll forget about it.")


@bot.command()
@commands.has_role("sas_manager")
async def check_partners(ctx):
    """Make sure that the partners match (manager only)"""
    role = get(ctx.guild.roles, name="sas_manager")
    if role not in ctx.author.roles:
        await ctx.channel.send("Only a SAS Manager can use this command")
        return

    def check(m):
        return m.author == ctx.author

    await ctx.author.send("Let's make sure these partners all make sense")
    await ctx.author.send("Your players are:\n  -%s" % '\n  -'.join([bot.family[n].name for n in bot.family]))

    partners_good = False
    while not partners_good:
        partners_good = True
        for n in bot.family:
            print(n, bot.family[n].name, bot.family[n].partner)
            if bot.family[n].partner not in [bot.family[k].name for k in bot.family]:
                print('Missing', bot.family[n].name)
                await ctx.author.send("%s has an unmatched partner (%s). Who should their partner be?" %
                                      (bot.family[n].name, bot.family[n].partner))
                try:
                    new_part = await bot.wait_for('message', check=check, timeout=30)
                except asyncio.TimeoutError:
                    return await ctx.author.send("You took too long")
                bot.family[n].partner = new_part.content
                partners_good = False

    await ctx.author.send("You should be good!")
    for user_id in bot.family:
        await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
    # async with bot.save_lock:
    #     await save_state(bot)


@bot.command()
@commands.has_role("sas_manager")
async def advance(ctx):
    """Advance the game to the next phase (managers only)"""
    print('Advance Command Entered')
    role = get(ctx.guild.roles, name="sas_manager")
    if role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.channel.send("You ready to move the game forward?")
    try:
        msg = await bot.wait_for('message', check=check, timeout=30)
    except asyncio.TimeoutError:
        return await ctx.channel.send("You took too long. Focus!")
    if msg.content.lower() != 'yes':
        await ctx.channel.send("Alright, I'll hold off. Just let me know")
        return
    await ctx.channel.send("Let's do it")

    if bot.game.status == 'Joining':
        await advance_game(bot)
        await ctx.channel.send("Time to select some tasks. Use !select to choose your task")
        return

    if bot.game.status == "Selecting":
        abort = False
        for n in bot.family:
            if len(bot.family[n].tasks) == 0 and bot.family[n].playing:
                await ctx.channel.send("%s hasn't chosen a task!" % bot.family[n].name)
                abort = True
        if abort:
            return await ctx.channel.send("Get those folks in, then try again")

        await advance_game(bot)
        await ctx.channel.send("Good luck everyone! \nYou can use !reveal to see whether you're the agent, " +
                               'and "!view tasks" to see your task(s)')


@bot.command()
@commands.dm_only()
async def select(ctx):
    """Select from the tasks and route cards available to you"""

    #  Abort if you aren't selecting or playing
    if bot.game.status not in ["Selecting", "Playing"]:
        return await ctx.channel.send("Silly goose, it's not time for that")

    #  Set basic variables.
    user_id = int(ctx.author.id)
    task_type = 'task'
    if bot.game.status == 'Playing':  # if playing, the only selections available are routes
        task_type = 'route'

    #  You can only select one task
    if bot.family[user_id].tasks and task_type == 'task':
        return await ctx.author.send("You've already chosen a task, goofball")

    #  You can't select a route if you don't have any held
    held_tasks = await asyncio.to_thread(get_all_held_tasks, user_id)
    if not held_tasks and task_type == 'route':
        return await ctx.author.send('You don\'t have any route cards to choose from. Use "!draw routes" to start')

    #  Relevant missions are the selection options, unless selecting a route
    rel_missions = bot.family[user_id].selections
    if task_type == 'route':
        rel_missions = await asyncio.to_thread(get_all_held_tasks, user_id)
    await ctx.author.send("Alright %s, these are your potential %ss:" % (bot.family[user_id].name, task_type))
    for k in rel_missions:
        await ctx.author.send(await format_task(k))

    #  Have the user make a selection
    msg = f"Choose wisely. Tell me which {task_type} you want"
    task_id = await select_task_via_buttons(bot, ctx, msg, rel_missions, include_exit=True)
    if task_id is None:  # User exited or timed out
        return await ctx.author.send("Take your time. I'll be here when you're ready, just give me a \"!select\"")
    cnfrm = await confirm_action(ctx, f"You're sure you want {task_type} {task_id}?")
    if not cnfrm:
        return await ctx.author.send("Take your time. I'll be here when you're ready, just give me a \"!select\"")

    # User is confirmed... time to lock it in
    task_id = int(task_id)
    if task_type == 'task':
        # Update the RAM variables
        bot.family[user_id].tasks.append(task_id)
        bot.missions[task_id].selected = True
        bot.missions[task_id].hold_for = None
        bot.missions[task_id].task_active = True
        # Update the database
        await ctx.author.send("Cool. You're locked in. Good Luck!")
        await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
        await asyncio.to_thread(save_mission_to_db, task_id, bot.missions[task_id])

        # Check if everyone has selected a task
        tasked_plus_npcs = [k for k in bot.family if bot.family[k].tasks or not bot.family[k].playing]
        if len(tasked_plus_npcs) == len(bot.family):
            print('Task selection suggests everyone is in')
            await send_orig_channel(ctx, "Everyone has chosen a task! Let's get this thing going!")
        else:
            still_choosing = [bot.family[k].name for k in bot.family if
                              (not bot.family[k].tasks) and bot.family[k].playing]
            if not still_choosing:
                still_choosing = "No one"
                print("Still choosing is 'no one'... I don't think you should be here")
            else:
                still_choosing = ", ".join(still_choosing)
            print(f'{ctx.author.name} chose a task. {still_choosing} are still choosing')

    else:  # task_type == route

        success, result = await finalize_route_selection(bot, ctx, user_id, chosen_route_id=task_id)
        if not success:
            return await ctx.author.send(f"Selection failed: {result}")

        # Reset route draw time for future draws
        bot.family[user_id].route_draw_time = None
        await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
        print("Saving in !select")


@bot.command()
@commands.dm_only()
@is_not_the_agent()
async def draw(ctx, draw_what=''):
    """Draws 3 route cards. You'll choose 1"""

    user_id = ctx.author.id
    print("Someone is drawing a route card!")
    if bot.game.status not in ["Playing"]:
        print("Draw command aborted because game not in Playing stage")
        return await ctx.channel.send("Silly goose, it's not time for that")
    if draw_what.lower() not in ['route', 'routes', '']:
        print("Unclear Draw Request")
        return await ctx.author.send("I'm not sure what you're trying to draw." +
                                     "This is really only good for route cards.\n Enter \"!draw routes\" to retry!")
    if bot.family[user_id].is_agent:
        return await ctx.author.send("The agent can't draw route cards. You have enough to worry about")

    active_routes = [k for k in bot.family[user_id].tasks  # all the user's tasks
                     if bot.missions[k].route_active and   # if they are active routes
                     not bot.missions[k].is_complete]      # and not complete
    if active_routes:
        print("User is trying to draw routes, but has incomplete routes")
        return await ctx.author.send("You have incomplete route cards drawn, so you can't draw more. "
                                     "Use \"!view\" to see your routes, and \"!complete\" to submit a completion")

    print("You are about to go into pending tasks")
    # if len(bot.family[ctx.author.id].pending_routes) > 0:
    list_held = await asyncio.to_thread(get_all_held_tasks, int(user_id))
    if list_held:
        print("User drawing routes has unselected tasks:", list_held)
        return await ctx.author.send('You already have route cards left to pick. Use "!view routes" to see them ' +
                                     'or "!select route" to pick one of them. ')

    # You have all the hints if you get 3x the agent's count, minus your original's three hints
    if len(bot.family[ctx.author.id].tasks) == (len(bot.family[bot.game.sas_ident].tasks)-1)*3:
        return await ctx.author.send("Geez. You've done enough routes to get all the hints. Take a vacation!")

    confirm_draw = await confirm_action(ctx, confirm_message="You're sure you want to draw routes? (yes/no)")
    if not confirm_draw:
        print("User aborted from drawing routes")
        return await ctx.author.send("No worries. You know where to find me. 😉")

    avail_routes = [k for k in bot.missions if bot.missions[k].route_eligible and not bot.missions[k].selected and
                    bot.missions[k].hold_for != int(ctx.author.id) and
                    bot.missions[k].submitter != ctx.author.id]

    if len(avail_routes) < 3:  # You don't have enough routes to choose from
        await send_orig_channel(ctx, 'Hey everyone! We need more route card ideas! Should we open submissions?')
        return await ctx.author.send("Sorry. We don't have enough eligible route cards. Get folks to add more!")

    print(bot.game.sas_ident)
    shuffle(avail_routes)
    user_id = int(ctx.author.id)

    # bot.family[user_id].pending_routes = [avail_routes[k].ident for k in range(3)]  # Not an object anymore
    for k in range(3):
        # bot.missions[avail_routes[k].ident].on_hold = True
        bot.missions[avail_routes[k]].hold_for = user_id
        await asyncio.to_thread(save_mission_to_db, avail_routes[k], bot.missions[avail_routes[k]])
        print("Assigned Routes")
    bot.family[ctx.author.id].route_draw_time = time.time()

    print(bot.game.sas_ident)
    await ctx.author.send("I've given you some choices. You can see them with \"!view routes\". "
                          "You have **24 hours** to pick one using \"!select\", or I will choose randomly!")

    print("Saving State in !draw before the timer")
    await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
    # async with bot.save_lock:
    #     await save_state(bot)

    print(bot.game.sas_ident)
    route_count = len([k for k in bot.missions if bot.missions[k].route_eligible and not bot.missions[k].selected])
    await send_orig_channel(ctx, f"Someone drew route cards. Once they pick one, there will be {len(avail_routes)-1}"
                                 f" of {route_count} remaining.")

    # --- THE BACKGROUND AUTO-TRIGGER ---
    async def route_deadline_countdown():
        print(f"[TIMER] Started 24h countdown for user {user_id}")
        await asyncio.sleep(86400)  # Sleep for 24 hours

        # Check if they still have pending routes. If empty, it means they already ran !select manually!
        held_routes = await asyncio.to_thread(get_all_held_tasks, user_id)
        if user_id in bot.family and held_routes:
            print(f"[TIMER] Deadline hit for user {user_id}! Triggering auto-selection...")
            await finalize_route_selection(bot, ctx, user_id, chosen_route_id=None)
        else:
            print(f"[TIMER] 24h check resolved: User {user_id} already made a manual selection.")

    # Fire and forget into the event loop
    asyncio.create_task(route_deadline_countdown())
    # -----------------------------------


@bot.command()
@commands.dm_only()
async def reveal(ctx):
    """Reveals your role and the person you're gifting to"""
    chan_check = await check_for_dm(ctx, failure_msg="You should only reveal your role in a private chat!")
    if not chan_check:
        return

    if bot.game.status != "Playing":
        return await ctx.author.send("It's not time for that yet!")

    await ctx.author.send("Let's do this! Drumroll please...")
    await asyncio.sleep(2)
    r = "ARE" if bot.family[ctx.author.id].is_agent else "ARE NOT"
    await ctx.author.send(f"You _**{r}**_ the secret agent this year!")
    s = "" if len(bot.family[ctx.author.id].tasks) == 1 else "s"
    await ctx.author.send(f'You can see your task{s} with the "!view tasks" command\n\u200B')
    await asyncio.sleep(1)
    await ctx.author.send(f'You are getting a gift for **{bot.family[ctx.author.id].gives_to}** this year!')


@bot.command()
@commands.dm_only()
async def complete(ctx):
    """Prove to Agent that route is complete. Get hint"""
    user_id = ctx.author.id

    if user_id not in bot.family:
        return await ctx.author.send("You aren't registered in the game!")

    print("User tasks in !complete: ", bot.family[user_id].tasks)
    print("Num tasks: ", len([k for k in bot.family[user_id].tasks if bot.missions[k].hold_for is not None]))

    if len([k for k in bot.family[ctx.author.id].tasks if bot.missions[k].hold_for == int(ctx.author.id) and
            not bot.missions[k].is_complete]) == 0:
        return await ctx.author.send("You don't have any route cards to complete, goofball")

    def check(m):
        return m.author.id == ctx.author.id and m.guild is None
    print("Retrieving Task ID")
    task_id = await select_task_via_buttons(bot, ctx, "Which route card did you complete?",
                                            [k for k in bot.family[ctx.author.id].tasks
                                             if bot.missions[k].route_eligible and
                                             bot.missions[k].hold_for == int(ctx.author.id) and
                                             not bot.missions[k].is_complete])
    if task_id is None:
        print("Task Completion confirm cancelled")
        return await ctx.author.send("Fair enough. Take your time.")
    print('task_id.content:', task_id, type(task_id))
    print('task list', bot.family[ctx.author.id].tasks)

    # 3. Prompt the user for the proof
    await ctx.author.send(f"Please send your text description and upload your image attachments now!")

    try:
        # Wait 2 minutes for them to upload/type everything
        proof_msg = await bot.wait_for('message', check=check, timeout=120.0)
    except asyncio.TimeoutError:
        return await ctx.author.send("Submission timed out. Please type `!submit` to try again.")

    # 4. Check if they actually provided text or images
    if not proof_msg.content and not proof_msg.attachments:
        return await ctx.author.send("It looks like you sent an empty message. Submission cancelled.")

    if proof_msg.attachments:
        submission_dir = "/home/eamonn_shirey/secret_agent_santa/route_submissions"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for k in range(len(proof_msg.attachments)):
            attachment = proof_msg.attachments[k]
            file_extension = os.path.splitext(attachment.filename)[1] or ".png"
            filename = f"{timestamp}_{str(user_id)}{file_extension}"
            full_save_path = os.path.join(submission_dir, filename)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as response:
                        if response.status == 200:
                            with open(full_save_path, "wb") as f:
                                f.write(await response.read())
            except Exception as e:
                await ctx.send("❌ A critical system error occurred while caching the image data.")
                print(f"Image Save Exception: {e}")

    if not bot.game.route_confirms:  # If the agent isn't confirming route cards
        print("Route confirms not active. Generating hint")
        await ctx.author.send("Alright, I trust you. Congrats on completing your route card!")

        player_name = bot.family[user_id].name
        # Generate a clean timestamp: YYYY-MM-DD HH:MM:SS
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_line = f"[{timestamp}] Player: {player_name}\nEntry: {proof_msg.content}\n{'-' * 40}\n"

        # 5. Thread-safe File Writing operation

            # Open in 'a' mode to append to the end without deleting past entries
        with open("journal.txt", "a", encoding="utf-8") as f:
            f.write(log_line)

        hint_cat = await complete_route(ctx, bot, ctx.author.id)
        bot.missions[task_id].is_complete = True
        if hint_cat is None:
            await ctx.author.send("I think you already have hints for every task...")
        else:
            await ctx.author.send('🕵️ Your hint has been generated. You can see hints with "!view hints"')
            await send_orig_channel(ctx, "🚨Someone just completed a route card and received a hint!🚨")


    else:  # If you're having the agent confirm route cards
        # 5. Confirm they want to send this to their target
        send_confirm = await confirm_action(ctx, "Are you ready to send this proof to **the agent**? (yes/no)")
        if not send_confirm:
            return await ctx.author.send("Cancelled. They won't see anything.")
        # 6. Fetch the recipient user object via the bot cache
        try:
            recipient = bot.get_user(int(bot.game.sas_ident))
        except discord.NotFound:
            return await ctx.author.send("Could not locate that player on Discord. Let the manager know.")
        # 7. Package and forward the payload
        await recipient.send(f"🔔 **Incoming route card proof from {bot.family[ctx.author.id].name} for " 
                             f"Route {task_id.content}!** 🔔")
        await recipient.send(await format_task(int(task_id.content)))
        # Forward text if they wrote any
        if proof_msg.content:
            await recipient.send(f"> {proof_msg.content}")
        # Forward attachments by passing the URLs directly into the message
        if proof_msg.attachments:
            for attachment in proof_msg.attachments:
                # Discord automatically embeds URLs if they point to an uploaded image file
                await recipient.send(attachment.url)

        # pending_confirms =await asyncio.to_thread(get_all_pending_tasks)
        # bot.game.sas.pending_confirms[task_id.content] = ctx.author.id
        bot.missions[int(task_id)].pending_confirms = int(ctx.author.id)

        await recipient.send(f'Please review the proof and confirm success/failure with "!confirm" You have 24 hours')
        await ctx.author.send(f"Your proof has been safely forwarded to the agent. You'll hear back once they approve.")

    print("Saving state in !complete")
    await asyncio.to_thread(save_mission_to_db, task_id, bot.missions[task_id])
    # async with bot.save_lock:
    #     await save_state(bot)


@bot.command()
@commands.check(lambda x: bot.game.route_confirms)
@commands.dm_only()
async def confirm(ctx):
    """The agent uses this to confirm route cards"""
    if not bot.game.route_confirms:
        return await ctx.author.send("🙉I'm surprised you were able to make that command. Ignoring... 🙉")

    user_id = ctx.author.id
    if ctx.author.id != bot.game.sas_ident:
        return await ctx.author.send(f"Seriously {bot.family[user_id].name}. Stop being difficult")
    def check(m):
        return m.author.id == user_id and m.guild is None

    pending = await asyncio.to_thread(get_all_pending_tasks)
    await ctx.author.send("Here are your pending confirmations")
    for p in pending:
        await ctx.author.send(await format_task(bot.missions[p]))
    task_id = await select_task_via_buttons(bot, ctx, "Which Route ID are you confirming?", pending)
    if task_id is None:
        return await ctx.author.send("Okay. I'll step aside for now")
    approve = await confirm_action(ctx, "Did they accomplish the task?")

    # Confirm the submitter details

    submitter_id = bot.missions[int(task_id)].pending_for
    # submitter_id = bot.game.sas.pending_confirms[task_id]
    submitter_name = bot.family[submitter_id].name
    try:
        recipient = await bot.fetch_user(int(submitter_id))
    except discord.NotFound:
        return await ctx.author.send("Could not locate that player on Discord. Let the manager know.")

    if not approve:  # Task is not approved
        await ctx.author.send(f"Boooo! What should I tell {submitter_name} that they need to do instead?")
        try:
            response = await bot.wait_for('message', check=check, timeout=30)
            msg = f"You're good for me to send that message back?\n> {response}"
            send_confirm = await confirm_action(ctx, confirm_message=msg)
            if not send_confirm:
                return ctx.author.send("Alright, aborting message! Try again when you're ready")
            await ctx.author.send("Sending rejection now")
            await recipient.send("Sorry. Your route card proof was rejected. The Agent had this to say:")
            await recipient.send(f"> {response.content}")
            await recipient.send("You'll need to resubmit proof to clear this route card")
        except asyncio.TimeoutError:
            await ctx.author.send("Message timeout error. Try again")

        await ctx.author.send("Messages sent. I'm sure you'll hear back from them soon")

    else:  # Task is approved
        await ctx.author.send(f"Hooray! I'll generate a hint and share it with {submitter_name} (and you)")

        print("Route is approved... let's do this")
        hint_cat = await complete_route(ctx, bot, submitter_id)
        if hint_cat is None:
            await recipient.send("It looks like you have hints for every task...")
            return await ctx.author.send("I think the submitter already has hints for every task...")

        await ctx.author.send("Alright, I'm going to pass this hint along")
        await recipient.send("Good news! The agent approved your route card completion!\n "
                             'You can  see all the hints you\'ve received with "!view hints"')
        await ctx.author.send('Message sent. If you want to see all the hints given, use "!view hints"')
        await send_orig_channel(ctx, "🚨Someone just completed a route card and received a hint!🚨")
        bot.missions[task_id].is_complete = True

    alert = bot.missions.get(task_id, None)
    if alert is None:
        print("!!! HEY you didn't remove a route confirm !!!")
    else:
        bot.missions[task_id].pending_for = None

    print("Saving state in !confirm")
    await asyncio.to_thread(save_mission_to_db, task_id, bot.missions[task_id])

    # async with bot.save_lock:
    #     await save_state(bot)


@bot.command()
@commands.has_role("sas_manager")
async def setdeadline(ctx, date_str=''):
    """Allows game managers to change the task submission cutoff date (Format: YYYY-MM-DD)"""

    # 1. Authority Validation Check
    role = get(ctx.guild.roles, name="sas_manager")
    if not role or role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command.")

    if bot.game is None:
        return await ctx.channel.send("There is no active game configuration loaded to set a deadline for!")

    if date_str == '':
        print("No date provided in setdeadline")
        return await ctx.channel.send("Please provide a date! Example usage: `!setdeadline 2026-07-01`")

    # 2. Syntax Validation: Ensure they formatted the date string correctly
    try:
        valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("Value error in syntax validation for setdeadline")
        return await ctx.channel.send(
            "❌ Invalid format. Please provide the deadline in exactly **YYYY-MM-DD** format. (e.g. `2026-07-01`)")

    # 3. Store and Save state
    bot.game.submission_deadline = date_str
    await asyncio.to_thread(save_game_to_db, bot)

    friendly_date = valid_date.strftime("%A, %B %d, %Y")
    await ctx.channel.send(f"✅ Success! Mission submissions via `!add` are now restricted after: **{friendly_date}**.")
    print(f"[MANAGER] Deadline successfully changed to {date_str} by {ctx.author.name}")


@bot.command()
@commands.dm_only()
async def journal(ctx, *, entry_text=""):
    """Allows players to log an anonymous or named thought/comment into journal.txt"""
    user_id = ctx.author.id

    if user_id not in bot.family:
        return await ctx.author.send("You need to register with `!join` before you can add journal entries.")

    # 2. Check if they just typed '!journal' empty, and prompt them if so
    if not entry_text.strip():
        await ctx.author.send("What would you like to record in your secret game journal? Type it out below:")

        def check(m):
            return m.author.id == user_id and m.guild is None

        try:
            print("Doing a journal entry")
            msg = await bot.wait_for('message', check=check, timeout=120.0)
            entry_text = msg.content
            print("Journal Entry complete: ", entry_text)
        except asyncio.TimeoutError:
            return await ctx.author.send("Journal entry timed out. Please type `!journal` to try again.")

    if not entry_text.strip():
        return await ctx.author.send("Journal entry was blank. Action cancelled.")

    # 3. Confirm submission using your button-based helper
    send_confirm = await confirm_action(ctx, "Are you ready to lock this entry into your game journal?\n> "+entry_text)
    if not send_confirm:
        return await ctx.author.send("Cancelled! I won't save this note.")

    # 4. Fetch details and build the text format
    player_name = bot.family[user_id].name
    # Generate a clean timestamp: YYYY-MM-DD HH:MM:SS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_line = f"[{timestamp}] Player: {player_name}\nEntry: {entry_text}\n{'-' * 40}\n"

    # 5. Thread-safe File Writing operation
    def write_to_file():
        # Open in 'a' mode to append to the end without deleting past entries
        with open("journal.txt", "a", encoding="utf-8") as f:
            f.write(log_line)

    try:
        # Run standard blocking file operations safely in a separate thread
        await asyncio.to_thread(write_to_file)

        await ctx.author.send(
            "📝 **Entry Logged!** Your thought has been securely locked in the confidential files.")
        print(f"[JOURNAL] Successfully recorded an entry for player '{player_name}'")

    except Exception as e:
        print(f"[ERROR] Failed writing to journal.txt: {e}")
        await ctx.author.send("❌ Ah, sorry! An unexpected database write failure happened. Let the manager know.")


@bot.command()
@commands.dm_only()
@is_the_manager()
async def pester(ctx, *, reminder_text=""):
    """Allows a SAS Manager to broadcast an official reminder to the main game channel"""

    # 1. Authority Validation Check
    role = discord.utils.get(ctx.guild.roles, name="sas_manager")
    if not role or role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command.")

    if bot.game is None:
        return await ctx.channel.send("There is no active game configuration loaded!")

    # 2. Prompt them if they just typed '!pester' completely empty
    if not reminder_text.strip():
        await ctx.channel.send("What would you like me to say to the group? Type it below:")

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            msg = await bot.wait_for('message', check=check, timeout=60.0)
            reminder_text = msg.content
        except asyncio.TimeoutError:
            return await ctx.channel.send("Pester command timed out.")

    if not reminder_text.strip():
        return await ctx.channel.send("Message was blank. Action cancelled.")

    # 3. Confirm using your button-based helper
    send_confirm = await confirm_action(ctx, f"Broadcast this to the main channel?\n> {reminder_text}")
    if not send_confirm:
        return await ctx.channel.send("Cancelled. No message sent.")

    # 4. Dispatch to the game channel using your existing helper function
    await send_orig_channel(ctx, reminder_text)

    # Send a confirmation notice back to the manager who invoked it
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.author.send("Sent!")


@bot.event
async def on_command_error(ctx, error):
    # 1. Unwrap the error if it is bundled inside a generic CommandInvokeError wrapper
    if isinstance(error, commands.CommandInvokeError):
        error = error.original

    # 2. 🧽 THE CLEANUP TRIGGER: Catch when a DM-only command is used in a server channel
    if isinstance(error, commands.PrivateMessageOnly):
        # Delete their public message immediately to keep the server channels clean
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print(f"⚠️ Missing Permissions: Could not delete message from {ctx.author} in #{ctx.channel.name}. Check bot roles.")
        except Exception as e:
            print(f"Error during message deletion: {e}")

        # Send a gentle, quiet reminder straight to their DMs instead
        try:
            await ctx.author.send(
                f"🤫 The `!{ctx.command.name}` command is a private tool. "
                f"I've cleaned up your message in the channel, so please continue your request right here!"
            )
        except discord.Forbidden:
            # This happens if the user completely blocked DM receipts from server members
            print(f"⚠️ Could not send redirect DM to {ctx.author.name} (DMs are locked).")
        return

    # Handle your other standard errors down here (like MissingRole, CommandNotFound, etc.)
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ You don't have permission to do that.")

@bot.command()
@commands.dm_only()
async def anonymous(ctx, *, message_text=""):
    """Allows a player to send an anonymous message to the channel or to players with matching tasks"""
    user_id = ctx.author.id
    print(f"{user_id} is sending an anonymous message!")
    if user_id not in bot.family:
        return await ctx.author.send("You need to register with `!join` first!")

    # 1. Grab text if they didn't provide any inline
    if not message_text.strip():
        await ctx.author.send("What anonymous message would you like to send as the bot? Type it below:")

        def check(m):
            return m.author.id == user_id and m.guild is None

        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
            message_text = msg.content
            print("Message Found")
        except asyncio.TimeoutError:
            print("Timeout Error")
            return await ctx.author.send("Command timed out.")

    if not message_text.strip():
        return await ctx.author.send("Message was blank. Action cancelled.")

    # 2. Build the routing destination options
    # We always offer the main channel option as choice ID '0'
    menu_options = [0]

    # Append any task IDs this specific player currently has active in their gameplay roster
    player_tasks = bot.family[user_id].tasks
    menu_options.extend(player_tasks)

    # Temporary injection: Inject a dummy title for ID '0' so our helper button generator reads it cleanly
    class TempMission:
        title = "📢 BROADCAST TO MAIN CHANNEL"

    bot.missions[0] = TempMission()

    # 3. Call your button selector helper!
    prompt = "Where should I route this anonymous message?"
    print("Looking for buttons")
    chosen_destination = await select_task_via_buttons(bot, ctx, prompt, menu_options, include_exit=True)

    # Clean up our temporary central channel dictionary injection immediately
    del bot.missions[0]

    if chosen_destination is None:
        return  # Player clicked Exit or timed out

    # 4. Final confirmation check
    send_confirm = await confirm_action(ctx, f"Are you ready to dispatch this anonymous message?\n> {message_text}")
    if not send_confirm:
        return await ctx.author.send("Cancelled.")

    # 5. Routing Delivery Execution
    if chosen_destination == 0:
        # Public Channel Routing
        channel = bot.get_channel(bot.game.game_channel)
        if channel:
            await channel.send(f"📬 **An anonymous message has arrived:**\n> {message_text}")
            await ctx.author.send("Sent safely to the public game channel!")
    else:
        # Task Matching Target Routing
        sent_count = 0
        for target_id, player in bot.family.items():
            # Don't send it back to the author, and match their task assignments
            if target_id != user_id and chosen_destination in player.tasks:
                try:
                    user_obj = await bot.fetch_user(target_id)
                    await user_obj.send(f"✉️ **Anonymous message regarding "
                                        f"Task {chosen_destination}:**\n> {message_text}")
                    sent_count += 1
                except Exception:
                    print(f"Failed to DM target player ID {target_id}")

        await ctx.author.send(f"Sent safely to the {sent_count} other player(s) who share Task {chosen_destination}!")


@bot.command()
@commands.dm_only()
@is_the_agent()
async def taunt(ctx, *, taunt_text=""):
    """Allows the Secret Agent to taunt individuals or the group anonymously"""
    user_id = ctx.author.id

    if user_id not in bot.family:
        return await ctx.author.send("You are not registered in the game database.")

    # 🔒 EXCLUSIVE AGENT GUARD RAIL
    if not getattr(bot.family[user_id], 'is_agent', False):
        return await ctx.author.send("❌ Access Denied. Only the **Secret Agent** can use this command!")

    # 1. Grab text if empty
    if not taunt_text.strip():
        await ctx.author.send("What would you like to say to taunt your players? Type it below:")

        def check(m):
            return m.author.id == user_id and m.guild is None

        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
            taunt_text = msg.content
        except asyncio.TimeoutError:
            return await ctx.author.send("Command timed out.")

    if not taunt_text.strip():
        return await ctx.author.send("Message was blank. Action cancelled.")

    # 2. Build the exact same menu destinations layout
    menu_options = [0]
    menu_options.extend(bot.family[user_id].tasks)

    class TempAgentMission:
        title = "📢 BROADCAST TAUNT TO MAIN CHANNEL"

    bot.missions[0] = TempAgentMission()

    # 3. Trigger button grid selection
    prompt = f"Where should I deliver this sinister agent taunt?"
    chosen_destination = await select_task_via_buttons(bot, ctx, prompt, menu_options, include_exit=True)

    del bot.missions[0]

    if chosen_destination is None:
        return

    # 4. Confirmation
    taunt_confirm = await confirm_action(ctx, f"Are you ready to send this agent taunt?\n> {msg}")
    if not taunt_confirm:
        return await ctx.author.send("Cancelled.")

    # 5. Routing Delivery Execution (Clearly calling out it's from the AGENT)
    if chosen_destination == 0:
        channel = bot.get_channel(bot.game.game_channel)
        if channel:
            await channel.send(
                f"🕵️‍♂️🚨 **A transmission from the SECRET AGENT has intercepted the feed:**\n> {taunt_text}")
            await ctx.author.send("Taunt broadcasted to the main group channel!")
    else:
        sent_count = 0
        for target_id, player in bot.family.items():
            if target_id != user_id and chosen_destination in player.tasks:
                try:
                    user_obj = await bot.fetch_user(target_id)
                    await user_obj.send(
                        f"🕵️‍♂️⚠️ **The Secret Agent is taunting you regarding Task"
                        f" {chosen_destination}:**\n> {taunt_text}")
                    sent_count += 1
                except Exception:
                    pass

        await ctx.author.send(
            f"Taunt whispered directly to the {sent_count} player(s) linked to Task {chosen_destination}!")


@bot.command()
@commands.has_role("sas_manager")
async def trigger_midgame_checkin(ctx):

    role = discord.utils.get(ctx.guild.roles, name="sas_manager")
    if not role or role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command.")

    # 1. (Your existing logic to broadcast check-in instructions to the channel goes here...)
    await ctx.send("📢 Mid-game check-ins have been requested! You have 48 hours to submit your suspicions.")
    for user_id in list(bot.family.keys()):
        print(f"Prompting check in from {user_id}")
        asyncio.create_task(prompt_user_feeling(user_id))

    # 2. Set the trigger deadline to exactly 48 hours from right now
    bot.game.reveal_timer_at = datetime.now() + timedelta(hours=48)

    # 3. Secure it into SQLite instantly
    await asyncio.to_thread(save_game_to_db, bot)

@bot.command()
@commands.has_role("sas_manager")
async def status_check(ctx):
    """Generates a readout of all the people who have registered and whether they've submitted tasks"""

    print("Generating a readout from !status_check")
    msg = "Current players:"
    for n in bot.family:
        name = bot.family[n].name
        task_count = len([k for k in bot.family[n].submissions if bot.missions[k].task_eligible])
        needs_tasks = 3 if bot.family[n].playing else 0
        if bot.family[n].playing:
            msg += f"\n- {name}: {task_count}/{needs_tasks} submitted"
        else:
            msg += f"\n- {name} is registered, but not playing"

    await ctx.channel.send(msg)

@bot.command()
@commands.has_role("sas_manager")
async def debug(ctx, name=''):
    """The manager uses this to debug the code"""
    print('\nDebug code entered!\n')
    print('family ids:', list(bot.family))
    print('family names:', [bot.family[k].name for k in bot.family])
    print(len(bot.missions), ' missions:', list(bot.missions))
    print('game:', bot.game.status, bot.game.game_channel, bot.game.expected_players)
    role = get(ctx.guild.roles, name="sas_manager")
    if role not in ctx.author.roles:
        return await ctx.channel.send("Only a SAS Manager can use this command")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    if name == '':
        await ctx.channel.send("Give me a name")
        try:
            msg = await bot.wait_for('message', check=check, timeout=5)
        except asyncio.TimeoutError:
            return await ctx.channel.send('Never mind...')
        name = msg.content

    if name not in [bot.family[k].name for k in bot.family]:
        print("Name not recognized")
        return
    for user in [k for k in bot.family if bot.family[k].name == name]:
        print('user:', user, bot.family[user].name, bot.family[user].partner, bot.family[user].is_agent)

    details_confirm = await confirm_action(ctx, "More Details?", send_to_author=False)
    if not details_confirm:
        return

    for user in [k for k in bot.family if bot.family[k].name == name]:
        print('More details:')
        print('submissions: ', bot.family[user].submissions)
        print('selections: ', bot.family[user].selections)
        print('tasks: ', bot.family[user].tasks)
        print('hints: ', bot.family[user].hints)


# 1. First, make sure you instantiate your custom class cog right below where it's defined:
async def main():
    # ... your existing setup logic, intents, database hydration, etc. ...

    # 🆕 REGISTER THE COG: Pass your bot object into the manager class
    # This wakes up the 5-minute background loop!
    await bot.add_cog(CheckInManager(bot))

    # Finally, start the bot engine
    async with bot:
        await bot.start(TOKEN)

# Run the async initialization script
# import asyncio

if __name__ == '__main__':
    asyncio.run(main())