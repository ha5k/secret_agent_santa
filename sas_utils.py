import pandas as pd
import pickle
import smtplib


class person(object):
    name = ''
    email = ''
    partner = ''
    playing = True
    submissions = []
    selections = []
    tasks = []
    is_agent = False
    gives_to = ''

    def __init__(self, name, email, partner, playing):
        self.name = name
        self.email = email
        self.partner = partner
        self.playing = playing


from random import shuffle

def read_form(url_in):
    url_use = url_in.replace('/edit#gid=', '/export?format=csv&gid=')
    if url_use == url_in:
        url_use = url_in.replace('/edit?resourcekey#gid=', '/export?format=csv&gid=')
    return pd.read_csv(url_use)

# def shuffle_tasks(df):
#
#     ## BUILD TASKS
#     tasks = []
#     for k in ['1', '2', '3']:
#         tmp = [x for x in df['task_' + k]]
#         tasks += tmp
#
#     fail_test = True
#     while fail_test:
#         fail_test = False
#
#         ## SHUFFLE TASKS
#         shuffle(tasks)
#         k = 0
#         tasks_per_person = 3
#         task_list = {}
#         for n in df['Who Are You?']:
#             per_tasks = []
#             for t in range(tasks_per_person):
#                 per_tasks.append(tasks[k + t])
#             task_list[n] = per_tasks
#             k += tasks_per_person
#
#         ## VALIDATE TASKS
#         for n in task_list:
#             for k in range(tasks_per_person):
#                 if df.loc[df.name == n, 'task_1'].values == task_list[n][k]:
#                     fail_test = True
#                     # print('Failed because:', n, task_list[n][k])
#
#     return (task_list)

def load_pickles():
    with open('family.pkl', 'rb') as f:
        family = pickle.load(f)
    with open('form_details.pkl', 'rb') as f:
        forms = pickle.load(f)
    with open('facilitator_details.pkl', 'rb') as f:
        facilitator = pickle.load(f)
    return family, forms, facilitator

def too_few_responses(submissions, form_to_send, family, facilitator):

    send_reminder = input('You want me to send a reminder email? (y/n) ')
    if send_reminder == 'y':
        responder_names = submissions['Who Are You?'].tolist()
        print('You got it, boss')

        with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
            server.starttls()
            server.login(facilitator['email'], facilitator['pwd'])

            for member in family:
                if responder_names.count(member) <= 0:
                    print('Following up with ', member)
                    message = '\n\n'.join([
                        f'Hey there {member}',
                        "It looks like like you haven't submitted tasks for Secret Agent Santa.",
                        "You wouldn't want to be put on the naughty list, would you?",
                        f'Please submit your tasks here:\n{form_to_send}',
                        "If you have any questions, get in touch with Eamonn! He can help!",
                        "Please advise,\nYour Secret Agent Santa Bot"
                    ])
                    server.sendmail(facilitator['email'], family[member].email, message)

def too_many_responses(submissions, family):
    responder_names = submissions['Who Are You?'].tolist()
    for member in family:
        if responder_names.count(member) > 1:
            print(f'\t{member} is duplicated')

    cont = input('Want to continue with the most recent submissions? (y/n)')
    if cont == 'y':
        submissions.drop_duplicates(subset = 'Who Are You?', keep = 'last', inplace = True)

    return submissions