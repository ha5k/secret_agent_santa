
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

if __name__ == "__main__":

    ## Load in Previous Session
    family, forms, facilitator = sas_utils.load_pickles()
    is_a_test = facilitator['is_test']

    ## SHARE THE SUBMISSIONS AND ASK FOR SELECTIONS
    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        subject = 'Subject: {}\n\n'.format('Select your Secret Agent Santa Task')
        if is_a_test:
            subject = 'Subject: {}\n\n'.format('TEST: Select your TEST Secret Agent Santa Task ('+str(round(time()))+')')
        for member in family:
            if family[member].playing:
                print('Sending message to: '+family[member].name)
                message = '\n'.join([
                    subject,
                    f"Greetings, {family[member].name}\n",
                    "It's time for you to select your Secret Agent Santa task. The Secret Agent will receive your selection as one of their tasks.\n",
                    "Remember, for the task to count, YOU have to do whatever task you select. Choose wisely.\n",
                    "The tasks you can choose from are:",

                    ## ESS-3: Updated to pull titles and details separately from new mission class
                    f"\nTask A: {family[member].selections[0].title}",
                    f"{family[member].selections[0].details}"
                    f"\n\nTask B: {family[member].selections[1].title}",
                    f"{family[member].selections[1].details}"
                    f"\n\nTask C: {family[member].selections[2].title}\n",
                    f"{family[member].selections[2].details}"
                    ## End ESS-3
                    
                    '\nYou can also choose "I am Feeling Lucky." If you do, you will be assigned a random task that someone else turned down.'
                    
                    "\nPlease make your selection here:",
                    forms['select_tasks'][0]+'\n',
                    'Best of Luck,',
                    'Your Secret Agent Santa Bot'
                ])

                if facilitator['send_emails']:
                    server.sendmail(facilitator['email'], family[member].email,
                                message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2013', '-').replace('\xe9',"[e-with-an-accent]").replace("\u2026",'...'))
                ## TODO This unicode replacement is rough. Consider fixing.

        facilitator['game_state'] = 'Get Selections'
        with open('facilitator_details.pkl', 'wb') as f:
            pickle.dump(facilitator, f)

