import ssl
import pandas
import smtplib
import pickle
import sas_utils
from time import time

## LOAD IN FAMILY AND FORM INFORMATION
family, forms, facilitator = sas_utils.load_pickles()
send_to = 'eamonn.shirey@gmail.com'

## SEND LINK TO SUBMIT TASKS
print('Opening Email Connection...')
with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
    print('Connection Opened!')
    server.starttls()
    server.login(facilitator['email'], facilitator['pwd'])
    subject = f'Subject: This is a test email ({round(time())})'

    message = '\n\n'.join([subject,
                           f'Hi -',
                           'This is a test email! Did you get it?',
                           'Cheers,\nYour Secret Agent Santa Bot'
                           ])
    server.sendmail(facilitator['email'], send_to, message)





