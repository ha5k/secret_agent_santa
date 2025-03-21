
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

## Read In Form for Drawing Route Cards
# family, forms, facilitator = sas_utils.load_pickles()
# route_requests = sas_utils.read_form(forms['draw_routes'][1])

# If it has a new entry, assign that person a username and add them to the family
for k in range(len(route_requests)):
    name = route_requests['Who Are You?'][k] + '_Bonus_' + route_requests['Timestamp'][k]
    email = route_requests['Email']
    if name not in family:
        family[name] = sas_utils.person(name, email, '', True)

# Go through the assignment process to get the new requesters tasks
unused_tasks = sas_utils.get_unused_tasks(family)
shuffle(unused_tasks)

send_routes_to = []
for nr in family:
    if len(family[nr].selections) == 0:
        send_routes_to.append(nr)
        for k in min(3, len(unused_tasks)):
            family[nr].selections.append(unused_tasks.pop(0))
            family[nr].selections[-1].selected = True

 # Email options and remove options from backup list

with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])

    for nr in send_routes_to:
        subject = 'Subject: {}\n\n'.format('Your Secret Agent Santa Bonus Route Cards')
        message = '\n'.join([
            subject,
            f"Hey there, {nr.split('_')[0]}\n",
            "You're a crazy person and asked for more tasks. It's too late to take it back now.\n",
            "The additional tasks you can choose from are:\n",

            f"\nTask A: {family[member].selections[0].title}",
            f"{family[member].selections[0].details}"
            f"\nTask B: {family[member].selections[1].title}",
            f"{family[member].selections[1].details}"
            f"\nTask C: {family[member].selections[2]}\n",
            f"{family[member].selections[2].details}"

            f"When selecting your task, the form will ask for a username. Your username for this round of drawing route cards is:{nr}",

            "\nPlease make your selection here:",
            forms['select_routes'][0] + '\n',

        ## Read in form for selecting new route cards
route_selections = sas_utils.read_form(forms['draw_routes'][1])



 # If it has an entry with assigned username and selection, confirm selection

 # Email confirmation to the chooser

 # Email the confirmed task to the secret agent
