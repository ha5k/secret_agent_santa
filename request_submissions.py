import pandas
import smtplib
import pickle

## LOAD IN FAMILY AND FORM INFORMATION

with open('family_details.pkl','r') as f:
    family = pickle.load(f)
with open('form_details.pkl','r') as f:
    forms = pickle.load(f)
with open('facilitator_details.pkl', 'r') as f:
    facilitator = pickle.load(f)

## SEND LINK TO SUBMIT TASKS

with smtplib.SMTP(smtp_server, smtp_port) as server:
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])
    for member in family:
        message = f'Subject: Secret Santa\n\nHi {member},\n\nPlease submit three tasks for the 2023 Edition of Secret Agent Santa at the following link:\n\n{forms[submit_tasks][0]}\n\nCheers,\nYour Secret Agent Santa Bot'
        server.sendmail(faciliator['email'], family[member]['email'], message)




