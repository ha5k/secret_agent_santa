
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

## Read In Form for Drawing Route Cards
family, forms, facilitator = sas_utils.load_pickles()
route_requests = sas_utils.read_form(forms['draw_routes'][1])

# If it has a new entry, assign that person a username and add them to the family
for k in range(len(route_requests)):
    name = route_requests['Who Are You?'][k] + route_requests['Timestamp'][k].replace(':','').replace(' ','').replace('/','')
    email = route_requests['What is Your Email?'][k]
    if name not in family:
        family[name] = sas_utils.person(name, email, '', True)

# Go through the assignment process to get the new requesters tasks


send_routes_to = []
print(send_routes_to)
for nr in family:
    print(nr)
    unused_tasks = sas_utils.get_unused_tasks(family)
    shuffle(unused_tasks)
    if len(family[nr].selections) == 0 and family[nr].playing:
        send_routes_to.append(nr)
        family[nr].selections = [unused_tasks[k] for k in range(min(3, len(unused_tasks)))]
        for k in family[nr].selections:
            k.selected = True
            print([len(family[k].selections) for k in family])
            print(family[list(family)[-1]].selections)


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

            f"\nTask A: {family[nr].selections[0].title}",
            f"{family[nr].selections[0].details}"
            f"\n\nTask B: {family[nr].selections[1].title}",
            f"{family[nr].selections[1].details}"
            f"\n\nTask C: {family[nr].selections[2].title}\n",
            f"{family[nr].selections[2].details}",

            f"When selecting your task, the form will ask for a secret code. Your secret code for this round of drawing route cards is: {nr}",

            "\nPlease make your selection here:",
            forms['select_routes'][0] + '\n',

            "\nBest of luck...",
            "Kringle. Kris Kringle"
        ])
        server.sendmail(facilitator['email'], family[nr].email,
                        message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                            '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                            "\u2026", '...'))

    ## Save the new pickle file
    with open('family.pkl', 'wb') as f:
        pickle.dump(family, f)
