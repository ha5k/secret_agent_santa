
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

## Load in Previous Session
family, forms, facilitator = sas_utils.load_pickles()
is_a_test = input("Type 'y' to confirm this is not a test: ")

## SHARE THE SUBMISSIONS AND ASK FOR SELECTIONS
with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])

with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])

    subject = 'Subject: {}\n\n'.format('Select your Secret Agent Santa Task')
    if is_a_test != 'y':
        subject = 'Subject: {}\n\n'.format('Select your TEST Secret Agent Santa Task ('+str(round(time()))+')')
    for member in family:
        print('Sending message to: '+family[member].name)
        message = '\n'.join([
            subject,
            f"Greetings, {family[member].name}\n",
            "It's time for you to select your Secret Agent Santa task. The Secret Agent will receive your selection as one of their tasks.\n",
            "Remember, for the task to count, YOU have to do whatever task you select. Choose wisely.\n",
            "The tasks you can choose from are:",
            f"\tTask A: {family[member].selections[0]}",
            f"\tTask B: {family[member].selections[1]}",
            f"\tTask C: {family[member].selections[2]}\n",
            "Please make your selection here:",
            forms['select_tasks'][0]+'\n',
            'Best of Luck,',
            'Your Secret Agent Santa Bot'
        ])

        server.sendmail(facilitator['email'], family[member].email,
                        message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'"))
        ## TODO This unicode replacement is rough. Consider fixing.



