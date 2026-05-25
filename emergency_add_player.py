import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
import random
from time import time

# LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES
family, forms, facilitator = sas_utils.load_pickles()

good_to_go = True
to_add = input('What player wants to be added? ')
verify = input('Confirm name of person who wants to be added: ')

good_to_go = True
if len(family[verify].tasks) > 0 or family[verify].playing:
    good_to_go = False
    print('Something went wrong. Abort!!!')

if to_add == verify and good_to_go:
    unused_tasks = []
    for member in family:
        unused_tasks += [x for x in family[member].selections if x not in family[member].tasks]

    random.shuffle(unused_tasks)
    tasks_to_send = [x for x in unused_tasks[:3]]

    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        subject = 'Subject: Your potential Secret Agent Santa Tasks'
        message = '\n'.join([
                       subject,
                       f"Hey, {family[verify].name}\n",
                       "Welcome to Secret Agent Santa!\n",
                        "Please choose a task below:",
                        '\t' + '\n\t'.join([str(k+1) + ': ' + unused_tasks[k] for k in range(3)]),
                        "\nCheers,\nSecret Agent Santa Bot"
                        ])

        server.sendmail(facilitator['email'], family[verify].email,
                        message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', '"')),

    task_select = input('Enter the Task Selected (1, 2, 3):')
    new_task = unused_tasks[int(task_select) - 1]

    family[verify].playing = True
    family[verify].tasks = [new_task]
    for member in family:
        if family[member].is_agent:
            family[member].tasks.append(new_task)

    #Save new Family File
    with open('family.pkl','wb') as f:
        pickle.dump(family, f)








