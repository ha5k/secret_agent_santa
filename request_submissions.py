import pandas
import smtplib
import pickle
import sas_utils

## LOAD IN FAMILY AND FORM INFORMATION
family, forms, facilitator = sas_utils.load_pickles()

## SEND LINK TO SUBMIT TASKS

with smtplib.SMTP(smtp_server, smtp_port) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])
    for member in family:
        message = '\n\n'.join([f'Subject: Secret Santa',
                               f'Hi {member}',
                               f'Please submit three tasks for the 2023 Edition of Secret Agent Santa at the following link:',
                               forms[submit_tasks][0],
                               'Cheers,\nYour Secret Agent Santa Bot'
                               ])
        server.sendmail(faciliator['email'], family[member]['email'], message)




