import ssl

import pandas
import smtplib
import pickle
import sas_utils
from time import time

## LOAD IN FAMILY AND FORM INFORMATION
family, forms, facilitator = sas_utils.load_pickles()
is_a_test = input("Type 'y' to confirm this is not a test: ")

## SEND LINK TO SUBMIT TASKS
print('Opening Email Connection...')
with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    print('Connection Opened!')
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])
    subject = f'Subject: Submit your tasks for Secret Agent Santa!'
    if is_a_test != 'y':
        subject = f'Subject: Submit your tasks for the TEST Secret Agent Santa! ({round(time())})'
    for member in family:
        member = 'Mom'
        print('Working on:',member)
        message = '\n\n'.join([subject,
                               f'Hi {member}',
                               f'Please submit three tasks for the 2023 Edition of Secret Agent Santa at the following link:',
                               forms['submit_tasks'][0],
                               'Cheers,\nYour Secret Agent Santa Bot'
                               ])
        server.sendmail(facilitator['email'], family[member][0], message)
        break




