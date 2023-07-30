import ssl

import pandas
import smtplib
import pickle
import sas_utils

## LOAD IN FAMILY AND FORM INFORMATION
family, forms, facilitator = sas_utils.load_pickles()

## SEND LINK TO SUBMIT TASKS
print('Opening Email Connection...')
with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    print('Connection Opened!')
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])
    for member in family:
        print('Working on:',member)
        message = '\n\n'.join([f'Subject: Secret Santa',
                               f'Hi {member}',
                               f'Please submit three tasks for the 2023 Edition of Secret Agent Santa at the following link:',
                               forms['submit_tasks'][0],
                               'Cheers,\nYour Secret Agent Santa Bot'
                               ])
        server.sendmail(facilitator['email'], family[member][0], message)




