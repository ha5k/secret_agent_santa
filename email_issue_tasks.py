import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
import random
from time import time


sas_gets_present = True  # Toggle whether the secret agent is also part of secret santa
personae_non_grata = []  # List of people not eligible for being the secret agent
is_a_test = input("Type 'y' to confirm this is not a test: ")

# LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES
family, forms, facilitator = sas_utils.load_pickles()


## SHARE THE TASKS AND THE INFO FOR THE SECRET AGENT

sas_gifting_msg = "Remember, the Secret Agent this year IS NOT part of secret santa. They don't get or give a gift."
if sas_gets_present:
    sas_gifting_msg = 'Remember, the Secret Agent this year IS part of secret santa. They get and give a gift.'

print('Formatting and sending emails...')
with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])

    subject = 'Subject: {}\n\n'.format('Your SECRET Secret Agent Santa Results')
    if is_a_test != 'y':
        subject = 'Subject: {}\n\n'.format('TEST: Your TEST Secret Agent Santa Results ( ' + str(round(time())) + ')')

    for member in family:

        if family[member].is_agent:  # Giver is the secret agent. Their tasks need to be a list
            task_string = 'You ARE the Secret Agent. Your mission objectives are ' \
                              'as follows:\n ' + '\n'.join(['\n' + task.title +'\n'+ task.details+'\nTask ID: '+task.id for task in family[member].tasks])
            preface = 'Time to work on your poker face because...'

            sas_tasks = [k for k in family[member].tasks]

            if sas_gets_present:
                preface = f'You have been randomly assigned to get a present for {family[member].gives_to}\n\nAlso... ' +preface
        elif family[member].playing:
            task_string = 'You are NOT the Secret Agent, but still have to ' \
                          'complete the mission you selected:\n- ' + family[member].tasks[0].title + '\n'+ family[member].tasks[0].details + '\nTask ID: '+family[member].tasks[0].id
            preface = f'You have been randomly assigned to get a present for {family[member].gives_to}\n\nAlso...'
        else:
            task_string = 'You have opted out of the agency this year. Probably wise!'
            preface = f'You have been randomly assigned to get a present for {family[member].gives_to}\n\nAlso...'

        message = '\n'.join([
            subject,
            f"Hey there, {member}\n",
            'Get excited, your Secret Agent Santa tasks are ready!  ' + sas_gifting_msg,
            '',
            preface,
            task_string,
            '',
            'HO HO HO,',
            'Your Secret Agent Santa Bot'
        ])
        server.sendmail(facilitator['email'], family[member].email,
                        message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2013', '-').replace('\xe9',"[e-with-an-accent]").replace("\u2026",'...'))

        print(f'\t...sent to {member} at {family[member].email}')
        family[member].task_emailed = True

    print('Sending Secret Tasks Email')
    message = '\n'.join([
        'subject: SECRET TASK LIST DETAILS FOR CEREMONY',
        '\n'.join(['THISISASECRETTHISISASECRETTHISISASECRET' for k in range(5)]),
        'THE SECRET TASKS ARE:',
        '\t' + '\n\t'.join([k.title + '\n' + k.details + '\nTask ID: '+k.id for k in sas_tasks]),
        '\nGood Luck'
    ])
    server.sendmail(facilitator['email'], facilitator['email'],
                    message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2013', '-').replace('\xe9',"[e-with-an-accent]").replace("\u2026",'...'))
    print('Ceremony Details Sent. Do not read them')

## Save the new pickle file
with open('family.pkl','wb') as f:
    pickle.dump(family, f)