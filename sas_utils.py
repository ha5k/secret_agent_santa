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
    task_emailed = False
    feels_lucky = False

    def __init__(self, name, email, partner, playing):
        self.name = name
        self.email = email
        self.partner = partner
        self.playing = playing

class mission(object):
    title = ''
    details = ''
    submitter = '' ## This is just the name of the person, not the object
    id = ''
    selected = False

    def __init__(self, title, details, submitter,id):
        self.title = title
        self.details = details
        self.submitter = submitter
        self.id = id
        self.selected = False





from random import shuffle

def get_unused_tasks(family):
    all_tasks = []
    for n in family:
        all_tasks += family[n].submissions

    return [k for k in all_tasks if not k.selected]

def read_form(url_in):
    url_use = url_in.replace('/edit#gid=', '/export?format=csv&gid=')
    if url_use == url_in:
        url_use = url_in.replace('/edit?resourcekey#gid=', '/export?format=csv&gid=')
    if url_use == url_in:
        url_use = url_in.replace('/edit?gid=','/export?format=csv&gid=')
    return pd.read_csv(url_use)
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
                if responder_names.count(member) <= 0 and family[member].playing :
                    print('Following up with ', member)
                    message = '\n\n'.join([
                        'Subject: Secret Agent Santa Needs You!',
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