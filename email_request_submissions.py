
import smtplib
import sas_utils
from sas_utils import person
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
        if family[member].playing:
            print('Working on: '+member)
            message = '\n\n'.join([subject,
                                   f'Hi {member}',
                                   f'Please submit three tasks for the 2024 Edition of Secret Agent Santa at the following link:',
                                   forms['submit_tasks'][0],
                                   'Cheers,\nYour Secret Agent Santa Bot'
                                   ])
            server.sendmail(facilitator['email'], family[member].email, message)
        else:
            print('Skipping ' + member + " because they're lame")
    print('Done requesting submissions!')
