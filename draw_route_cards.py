
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
    name = route_requests['Who Are You?'][k] + '_' + route_requests['Timestamp'][k]
    email = route_requests['Email']
    if name not in family:
        family[name] = sas_utils.person(name, email, '', True)

# Go through the assignment process to get the new requesters tasks
unused_tasks = sas_utils.get_unused_tasks(family)
shuffle(unused_tasks)

for nr in family:
    if len(family[nr].selections) == 0:
        for k in min(3, len(unused_tasks)):
            family[nr].selections.append(unused_tasks.pop(0))
            family[nr].selections[-1].selected = True

 # Email options and remove options from backup list

## Read in form for selecting new route cards

 # If it has an entry with assigned username and selection, confirm selection

 # Email confirmation to the chooser

 # Email the confirmed task to the secret agent
