
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

## Read In Form for Drawing Route Cards
family, forms, facilitator = sas_utils.load_pickles()
tasks = sas_utils.load_tasks()
mc = sas_utils.read_form(forms['message_center'][1])

## Check whether you have new messages
if len(mc) > facilitator['messages_sent']:
    k = 0
    ## iterate through every row of the messages
    for r in mc.iterrows():

        ## If you haven't already sent the message
        if k >= facilitator['messages_sent']:
            task = r[1]["What is the Task ID? (It's a four digit number)"]
            m = r[1]["What message are you sending? "]

            print(task, m)

            send_to = []
            for member in family:
                st = False
                for f in family[member].submissions:
                    if f.id == task:
                        send_to.append(member)
                for f in family[member].selections:
                    if f.id == task:
                        send_to.append(member)
            print('Hey')
            with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
                server.starttls()
                server.login(facilitator['email'], facilitator['pwd'])

                for member in send_to:
                    subject = 'Subject: {}\n\n'.format('You have a new SAS message')
                    message = '\n'.join([
                        subject,
                        f"Hey there, {member}\n",
                        "Somebody asked a question or sent a message about a task. You're either doing that task or submitted it!\n",

                        f"The task in question is Task ID: {task}",
                        f"The task is: {tasks[task].title}",
                        f"{tasks[task].details}",

                        f"\nThe question is...",
                        f"{m}",

                        "\nYou can respond to this message at the link below:",
                        f"{forms['message_center'][0]}",


                        "\nBe kind, rewind,",
                        "The SAS Team"
                    ])
                    server.sendmail(facilitator['email'], family[member].email,
                                    message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d','"').replace(
                                        '\u2018', "'").replace('\u2013', '-').replace('\xe9',"[e-with-an-accent]").replace(
                                        "\u2026", '...'))

        k += 1
        ##

    facilitator['messages_sent'] = k
