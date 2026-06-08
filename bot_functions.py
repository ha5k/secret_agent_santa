# import discord
# from discord.ext import commands
# from discord.utils import get
import asyncio
import pickle
from random import shuffle, choice
from hint_generator import *
import random

from db_manager import get_all_held_tasks, save_player_to_db, save_mission_to_db, save_game_to_db, \
    save_player_hints_to_db


# async def save_state(bot, suffix=''):
#     def blocking_save():
#         with open(f"game{suffix}.pkl", "wb") as f:
#             pickle.dump(bot.game, f)
#         with open(f"family{suffix}.pkl", "wb") as f:
#             pickle.dump(bot.family, f)
#         with open(f"missions{suffix}.pkl", "wb") as f:
#             pickle.dump(bot.missions, f)
#
#     await asyncio.to_thread(blocking_save)  # Offloads disk lag completely!


async def reset_tasks(bot):
    """ Resets the tasks and submissions if you fail a shuffle"""
    print('Shuffle failed... resetting')
    for user_id in bot.family:
        bot.family[user_id].selections = []
        await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])

    for task_id in bot.missions:
        bot.missions[task_id].selected = False
        await asyncio.to_thread(save_mission_to_db, task_id, bot.missions[task_id])
    print('Trying Again!')
    return


async def shuffle_tasks(bot, tasks_to_assign = 3):
    """ Shuffle the tasks and assign them randomly to the family"""
    print('Shuffling Tasks for Selection')
    shuffles_good = False
    while not shuffles_good:
        shuffles_good = True
        pending_tasks = []
        for f in bot.family:
            if bot.family[f].playing:
                while len(bot.family[f].selections) < tasks_to_assign:
                    print(f'Assigning tasks for {f}')
                    tasks = [m for m in bot.missions if ((m not in pending_tasks) and
                                                         (bot.missions[m].submitter != f) and
                                                         (bot.missions[m].task_eligible))]
                    shuffle(tasks)
                    if len(tasks) == 0:  # You're out of options for tasks
                        shuffles_good = False
                        await reset_tasks(bot)
                        break
                    task = tasks.pop(0)
                    bot.family[f].selections.append(task)
                    pending_tasks.append(task)

                if not shuffles_good:  # You need to also break out of the for loop
                    print("Shuffles were bad. Try again")
                    break
        for user_id in bot.family:
            await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])
            for s in bot.family[user_id].selections:
                bot.missions[s].selection_for = user_id
                await asyncio.to_thread(save_mission_to_db, s, bot.missions[s])
    return

async def assign_giftees(bot):
    """Assigns gift recipients to givers across the family"""
    names = [bot.family[n].name for n in bot.family]

    good_pairing = False
    while not good_pairing:
        good_pairing = True
        shuffle(names)
        for k in range(len(names)):
            giver = bot.family[list(bot.family)[k]].name
            part = bot.family[list(bot.family)[k]].partner
            givee = names[k]
            if giver == givee or part == givee:
                good_pairing = False
                print('Bad Pairing! Try again!')
                break
    print('Pairings Should be Good!')
    for k in range(len(names)):
        bot.family[list(bot.family)[k]].gives_to = names[k]
    for user_id in bot.family:
        await asyncio.to_thread(save_player_to_db, user_id, bot.family[user_id])

    return

async def assign_sas(bot):
    """This determines who the Secret Agent will be, then updates their task list"""

    png = []  # The names of the people that you want to block from being the agent
    players = [k for k in bot.family if bot.family[k].playing and bot.family[k].name not in png]
    sas = choice(players)
    # print("assign SAS: ", sas)

    bot.family[sas].is_agent = True
    bot.family[sas].tasks = [k for k in bot.missions
                             if bot.missions[k].selected and bot.missions[k].task_eligible]
    print("assign SAS: ", sas)
    bot.game.sas_ident = sas
    print(bot.game.sas_ident)
    await asyncio.to_thread(save_player_to_db, bot.game.sas_ident, bot.family[bot.game.sas_ident])
    await asyncio.to_thread(save_game_to_db, bot)
    return



async def advance_game(bot):
    if bot.game.status == 'Joining':
        # async with bot.save_lock:
        #     await save_state(bot, '_joining')
        await shuffle_tasks(bot)
        bot.game.status = 'Selecting'
        await asyncio.to_thread(save_game_to_db, bot)
        # async with bot.save_lock:
        #     await save_state(bot)
        return

    if bot.game.status == "Selecting":
        # async with bot.save_lock:
        #     await save_state(bot, '_selecting')
        await assign_giftees(bot)
        await assign_sas(bot)
        print("You have a secret Agent now!")
        bot.game.status = 'Playing'
        await asyncio.to_thread(save_player_to_db, bot.game.sas_ident, bot.family[bot.game.sas_ident])
        await asyncio.to_thread(save_game_to_db, bot)
        # async with bot.save_lock:
        #     await save_state(bot)
        return


def check_status(bot, desired_state='Joining'):
    """This checks whether a command is active based on the game status"""
    return bot.game.status == desired_state


async def complete_route(ctx, bot, submitter_id):
    """Picks a new task/category save hint to hints dict"""

    print("Confirming a route in complete_route")

    # Select a new task to hint
    rel_hints = [k for k in bot.family[bot.game.sas_ident].tasks if
                 len(bot.family[submitter_id].hints.get(k, {})) < 3 and
                 bot.missions[k].task_eligible and k not in bot.family[submitter_id].tasks]

    if len(rel_hints) == 0:  #Somehow, they have three hints for every task
        return None
    hint_id = choice(rel_hints)

    # Select a category to hint
    rel_cats = [k for k in range(3) if k not in list(bot.family[submitter_id].hints.get(hint_id, []))]
    cat_id = choice(rel_cats)

    # Generate the hint
    print(f"Unlocking a hint for Task {hint_id}, Category {cat_id}")

    # hint = ''
    # if cat_id == 0: # Hint is the title
    #     hint = bot.missions[hint_id].title
    # elif cat_id == 1: # Hint is the two words
    #     hint = generate_cryptic_clue(bot.missions[hint_id].details)
    # else:  # cat_id == 3, Hint is the image
    #     hint = generate_mission_image(bot.missions[hint_id].details)

    # Save the hint to the people who deserve it
    bot.family[submitter_id].hints.get(hint_id, {})[cat_id] = True
    if not bot.family[submitter_id].hints.get(hint_id, {}):
        bot.family[submitter_id].hints[hint_id] = {cat_id: True}
    else:
        bot.family[submitter_id].hints[hint_id][cat_id] = True

    print("Update: ", bot.family[submitter_id].hints.get(hint_id, {})[cat_id])

    if bot.game.route_confirms:  # If the agent also gets a hint
        sas = bot.game.sas_ident
        if not bot.family[sas].hints.get(hint_id, {}):
            bot.family[sas].hints[hint_id] = {cat_id: True}
        else:
            bot.family[sas].hints[hint_id][cat_id] = True

        # bot.family[bot.game.sas_ident].hints[hint_id][cat_id] = True
        # bot.family[bot.game.sas_ident].hints[hint_id][cat_id] = hint

    await asyncio.to_thread(save_player_hints_to_db, submitter_id, bot.family[submitter_id].hints)
    await asyncio.to_thread(save_player_hints_to_db, bot.game.sas_ident, bot.family[bot.game.sas_ident].hints)
    # async with bot.save_lock:
    #     await save_state(bot)
    return cat_id

async def finalize_route_selection(bot, ctx, user_id: int, chosen_route_id: int = None):
    """
    The core selection engine. If chosen_route_id is provided, it locks it in.
    If chosen_route_id is None, it selects one at random from their pending list.
    """
    # 1. Double check they actually have routes on hold
    if user_id not in bot.family or not await asyncio.to_thread(get_all_held_tasks, user_id):
        return False, "No held routes found."

    on_hold = await asyncio.to_thread(get_all_held_tasks, user_id)

    # 2. Fallback: If they timed out, choose a random one for them
    is_auto_selection = False
    if chosen_route_id is None:
        chosen_route_id = random.choice(on_hold)
        is_auto_selection = True
    elif chosen_route_id not in on_hold:
        return False, "Invalid Route ID chosen."

    # 3. Lock it into the database structures
    bot.family[user_id].tasks.append(chosen_route_id)
    bot.missions[chosen_route_id].selected = True
    bot.missins[chosen_route_id].route_active = True
    await asyncio.to_thread(save_mission_to_db, chosen_route_id, bot.missions[chosen_route_id])

    # 4. Release the remaining choices back into the general pool
    unselected_routes = [k for k in on_hold if k != chosen_route_id]
    for k in unselected_routes:
        bot.missions[k].hold_for = None
        await asyncio.to_thread(save_mission_to_db, k, bot.missions[k])

    # 5. Commit the save state securely
    print("Saving state in finalize_route_selection")

    # 6. Notify the user based on how it happened
    try:
        user = await bot.fetch_user(user_id)
        if is_auto_selection:
            await user.send(
                f"⏰ **24-Hour Deadline Passed!** You didn't select a route in time, "
                f"so I have automatically assigned you **Task {chosen_route_id}**! Good luck."
            )
        else:
            await user.send(f"Cool. You're locked into Route **Task {chosen_route_id}**. Good Luck!")
    except Exception as e:
        print(f"Failed to DM user {user_id}: {e}")

    return True, chosen_route_id


class AgentPollView(discord.ui.View):
    def __init__(self, bot, voter_id: int):
        # Set a generous 1-hour timeout for the buttons to stay active
        super().__init__(timeout=3600.0)
        self.bot = bot
        self.voter_id = voter_id
        self.chosen_suspect = None

        # Dynamically build a button for every playing member in the family
        for player_id, player in self.bot.family.items():
            # Optional safety rule: Don't let them vote for themselves
            if player_id == voter_id:
                continue

            if player.playing:
                # We use the player's unique ID as the button's custom_id
                button = discord.ui.Button(
                    label=player.name,
                    style=discord.ButtonStyle.secondary,
                    custom_id=str(player_id)
                )
                # Attach our click handler to the button
                button.callback = self.make_callback(player_id, player.name)
                self.add_item(button)

    def make_callback(self, suspect_id, suspect_name):
        """Creates an isolated callback function for each button click"""

        async def callback(interaction: discord.Interaction):
            # Ensure only the targeted user can press these buttons
            if interaction.user.id != self.voter_id:
                return await interaction.response.send_message("This isn't your poll!", ephemeral=True)

            self.chosen_suspect = suspect_name

            # Disable all buttons, so they can't double-click or change their mind
            for child in self.children:
                child.disabled = True

            # Update the message to show their confirmation lock
            await interaction.response.edit_message(
                content=f"🔒 Lock it in! You suspected: **{suspect_name}**.",
                view=self
            )
            # Stop listening for more button inputs
            self.stop()

        return callback

    async def on_timeout(self):
        """Fires automatically if the user takes longer than an hour to choose"""
        for child in self.children:
            child.disabled = True
        self.stop()


class ConfirmView(discord.ui.View):
    def __init__(self, voter_id: int):
        super().__init__(timeout=60.0)
        self.voter_id = voter_id
        self.value = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.voter_id:
            return await interaction.response.send_message("This isn't your choice!", ephemeral=True)

        # 1. 🆕 Defer the response instantly! This buys you 15 minutes of safety.
        await interaction.response.defer()

        self.value = True
        for child in self.children:
            child.disabled = True

        # 2. 🆕 Since we deferred, we use interaction.message.edit instead of response.edit_message
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.voter_id:
            return await interaction.response.send_message("This isn't your choice!", ephemeral=True)

        # 1. 🆕 Defer here too!
        await interaction.response.defer()

        self.value = False
        for child in self.children:
            child.disabled = True

        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        self.stop()


async def confirm_action(ctx, confirm_message="Are you sure?", send_to_author=True):
    """
    Asks a user a yes/no question using buttons.
    Returns True if they click Yes, False if they click No or time out.
    """

    print(f"\tConfirming Action for: {ctx.author.id}")
    # 1. Instantiate the button view locked to this specific user's ID
    view = ConfirmView(voter_id=ctx.author.id)

    # 2. Send the message with the buttons attached
    if send_to_author:
        msg = await ctx.author.send(confirm_message, view=view)
    else:
        msg = await ctx.send(confirm_message, view=view)

    # 3. Wait right here until a button is clicked, or it times out
    await view.wait()

    # Optional cleanup: Clean up the message text to show the session closed
    try:
        if view.value is True:
            await msg.edit(content=f"{confirm_message} *(Confirmed)*")
        elif view.value is False:
            await msg.edit(content=f"{confirm_message} *(Selected No)*")
        else:
            await msg.edit(content=f"{confirm_message} *(Cancelled/Timed out)*")
    except Exception:
        pass  # Safeguard in case the message was deleted

    # 4. Return the outcome (True or False)
    return view.value if view.value is not None else False


class TaskSelectionView(discord.ui.View):
    def __init__(self, bot, voter_id: int, task_ids: list, include_exit: bool = True, hide_titles: bool = False):

        # 1 hour timeout for the selection grid
        super().__init__(timeout=3600.0)
        self.bot = bot
        self.voter_id = voter_id
        self.chosen_task_id = None
        self.exited = False  # Track if they clicked the exit button

        # 1. Dynamically build a button for every task ID passed in
        for task_id in task_ids:
            print("Task ID:", task_id)
            task_title = self.bot.missions[task_id].title
            short_label = task_title if len(task_title) <= 60 else f"{task_title[:57]}..."
            if hide_titles:
                short_label = ''
            task_type = 'Task'
            if task_id == 0 or (not bot.missions[int(task_id)].task_eligible or
                                bot.missions[int(task_id)].hold_for is not None):
                task_type = 'Route'

            if task_id != 0:
                if task_type == 'Route' and bot.missions[int(task_id)].is_complete:
                    task_type = '✅ Route'

            print("Creating Button")
            button = discord.ui.Button(
                label=f"{task_type} {task_id}: {short_label}",
                style=discord.ButtonStyle.secondary,
                custom_id=str(task_id)
            )
            print("Calling button")
            button.callback = self.make_callback(task_id)
            print("Adding button")
            self.add_item(button)

        # 2. 🆕 Conditionally append a dark charcoal "Exit" button at the end
        if include_exit:
            print("Including Exit")
            exit_button = discord.ui.Button(
                label="Exit Menu",
                style=discord.ButtonStyle.secondary,  # Dark slate gray color
                emoji="🚪",
                custom_id="exit_menu_action"
            )
            exit_button.callback = self.make_exit_callback()
            self.add_item(exit_button)

    def make_callback(self, task_id: int):
        """Creates an isolated click response for a task button"""

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.voter_id:
                return await interaction.response.send_message("This isn't your menu!", ephemeral=True)

            self.chosen_task_id = task_id

            # Disable all components upon click
            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(view=self)
            self.stop()

        return callback

    def make_exit_callback(self):
        """🆕 Handles the Exit button click event"""

        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.voter_id:
                return await interaction.response.send_message("This isn't your menu!", ephemeral=True)

            self.exited = True
            self.chosen_task_id = None  # Ensure no task is returned

            for child in self.children:
                child.disabled = True

            await interaction.response.edit_message(view=self)
            self.stop()

        return callback

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        self.stop()


async def select_task_via_buttons(bot, ctx, prompt_message: str, task_ids: list,
                                  include_exit: bool = False, hide_titles: bool = False):
    """
    Sends a message with dynamic buttons for each task ID in the list.
    Includes an optional manual exit button (defaults to False).
    Returns the integer task_id, or None if they click exit, cancel, or time out.
    """
    user_id = ctx.author.id
    print("you made it")

    if not task_ids:
        await ctx.send("There are no tasks available to select from.")
        print("No tasks found")
        return None
    # Pass the include_exit flag down into the view generator
    print("About to send prompt")
    view = TaskSelectionView(bot, user_id, task_ids, include_exit=include_exit, hide_titles=hide_titles)
    print("Sending prompt")
    msg = await ctx.send(prompt_message, view=view)
    print("Buttons sent")
    await view.wait()

    try:
        if view.exited:
            await msg.edit(content=f"{prompt_message}\n🚪 *Menu exited by player.*")
        elif view.chosen_task_id is not None:
            await msg.edit(content=f"{prompt_message}\n🔒 *Selected: Task {view.chosen_task_id}*")
        else:
            await msg.edit(content=f"{prompt_message}\n❌ *Selection timed out.*")
    except Exception:
        print("Exception raised in select task via buttons!")
        pass

    return view.chosen_task_id


def get_user_id_by_name(bot, target_name: str) -> int | None:
    """
    Scans bot.family to convert a raw text username/nickname into a Discord user_id.
    Returns the integer user_id if found, otherwise returns None.
    """
    if not target_name:
        return None

    target_name = target_name.strip().lower()

    # Loop through the memory matrix to match against the person object's name property
    for user_id, player_obj in bot.family.items():
        # Using getattr safely prevents errors if a player object doesn't have a name yet
        player_name = getattr(player_obj, 'name', '')
        if player_name and player_name.lower() == target_name:
            return user_id

    return None
def count_suspicions(bot, target_id: int) -> int:
    """Counts how many OTHER active players suspect the target_id"""
    count = 0
    for uid, player in bot.family.items():
        if uid == target_id:
            continue

        # Verify they actually submitted a mid-game feeling,
        # and see if they named this person as the secret agent
        # (Using the method we set up earlier to resolve names to user_ids)
        suspect_name = getattr(player, 'midpoint_feeling', None)
        if suspect_name:
            suspect_id = get_user_id_by_name(bot, suspect_name)
            if suspect_id == target_id:
                count += 1
    return count


from discord.ext import commands


def is_the_agent():
    """
    Custom check decorator. Blocks execution and hides the command from !help
    if the player is currently the designated Secret Agent.
    """

    async def predicate(ctx):
        # 1. Safety check: If it's a DM, make sure we have their player profile loaded
        user_id = ctx.author.id

        if user_id not in ctx.bot.family:
            # If they aren't in the active game tracking registry, block them
            raise commands.CheckFailure("You are not registered in the active game roster.")

        player = ctx.bot.family[user_id]

        # 2. Check the restriction characteristics
        # Assuming player.is_agent is a Boolean, or cross-referencing bot.game.sas_ident
        is_agent_by_profile = getattr(player, 'is_agent', False)
        is_agent_by_global_id = (ctx.bot.game.sas_ident == user_id)

        if is_agent_by_profile or is_agent_by_global_id:
            # Returning False here automatically hides the command from their !help menu
            # and blocks them from running it!
            return True

        return False

    return commands.check(predicate)


def is_not_the_agent():
    """Negates the existing is_the_agent check blueprint dynamically"""
    # 1. Grab the underlying logic function (.predicate) inside the check
    original_check = is_the_agent()

    async def predicate(ctx):
        return not await original_check.predicate(ctx)

    # 2. Return a new command check that runs the old one and flips the result with 'not'
    return commands.check(predicate)
def is_the_manager():
    """
    Custom check decorator. Blocks execution and hides the command from !help
    if the player is not in the specified "managers" list.
    """

    managers = ["Eamonn"]
    async def predicate(ctx):
        # 1. Safety check: If it's a DM, make sure we have their player profile loaded
        user_id = ctx.author.id

        if user_id not in ctx.bot.family:
            # If they aren't in the active game tracking registry, block them
            raise commands.CheckFailure("You are not registered in the active game roster.")

        player = ctx.bot.family[user_id]

        # 2. Check the restriction characteristics
        # Assuming player.is_agent is a Boolean, or cross-referencing bot.game.sas_ident
        is_mgr_by_profile = getattr(player, 'name', '') in managers

        if is_mgr_by_profile:
            # Returning False here automatically hides the command from their !help menu
            # and blocks them from running it!
            return True

        return False

    return commands.check(predicate)
