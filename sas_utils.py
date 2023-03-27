import pandas as pd

def read_form(url_in):
    url_use = url_in.replace('/edit#gid=', '/export?format=csv&gid=')
    return pd.read_csv(url_use)

def shuffle_tasks(df):

    ## BUILD TASKS
    tasks = []
    for k in ['1', '2', '3']:
        tmp = [x for x in df['task_' + k]]
        tasks += tmp

    fail_test = True
    while fail_test:
        fail_test = False

        ## SHUFFLE TASKS
        shuffle(tasks)
        k = 0
        tasks_per_person = 3
        task_list = {}
        for n in df.name:
            per_tasks = []
            for t in range(tasks_per_person):
                per_tasks.append(tasks[k + t])
            task_list[n] = per_tasks
            k += tasks_per_person

        ## VALIDATE TASKS
        for n in task_list:
            for k in range(tasks_per_person):
                if df.loc[df.name == n, 'task_1'].values == task_list[n][k]:
                    fail_test = True
                    # print('Failed because:', n, task_list[n][k])

    return (task_list)

def load_pickles():
    with open('family_details.pkl', 'r') as f:
        family = pickle.load(f)
    with open('form_details.pkl', 'r') as f:
        forms = pickle.load(f)
    with open('facilitator_details.pkl', 'r') as f:
        facilitator = pickle.load(f)
    return family, forms, facilitator


### OLD  CODE
'''
import pandas as pd
import smtplib
import ssl
import pickle
import sas_utils

with open('test.pkl', 'rb') as file:
    vars = pickle.load(file)
port = vars[0]
password = vars[1]


smtp_server = "smtp.gmail.com"
sender_email = "kylesgonnahatethis@gmail.com"  # Enter your address
receiver_email = "eamonn.shirey@gmail.com"  # Enter receiver address
message = """\
Subject: Hi there

This message is sent from Python."""

context = ssl.create_default_context()
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message)



target = 'https://docs.google.com/spreadsheets/d/1FTQo7Int8YRHdBe6-QRKzJ0dr1uU3SZLaHRypyWudiY/edit#gid=1372196122'
df = sas_utils.read_proposals(target)
'''