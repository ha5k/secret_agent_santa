import pandas as pd
import pickle
import smtplib


class sas_obj(object):
    """Object to hold details relevant to the agent as a role"""
    def __init__(self, ident=None):
        self.id = ident
        self.pending_confirms = {}


class gameState(object):
    status = 'Joining' #(Joining, Selecting, Playing, Settled)
    expected_players = 10
    actual_players = 0
    game_channel = ''
    sas = sas_obj()
    route_confirms = False
    checkin_date = None
    checkin_sent = False

    def __init__(self, status, expected_players, actual_players, game_channel, route_confirms=False):
        self.status = status
        self.expected_players = expected_players
        self.actual_players = actual_players
        self.game_channel = game_channel
        self.sas_ident = None
        self.route_confirms = route_confirms
        self.submission_deadline = "2026-07-01"
        self.checkin_date = None
        self.checkin_sent = False
        self.submitters_see_hints = True


class person(object):
    name = ''
    email = ''
    partner = ''
    playing = True
    def __init__(self, name, email, partner, playing):
        self.name = name
        self.email = email
        self.partner = partner
        self.playing = playing

        self.submissions = []
        self.selections = []
        self.pending_routes = []
        self.tasks = []
        self.hints = {}
        self.is_agent = False
        self.gives_to = ''
        self.task_emailed = False
        self.feels_lucky = False
        self.route_draw_time = None
        self.checkin_feeling = ""

class mission(object):
    title = ''
    details = ''
    submitter = '' ## This is just the name of the person, not the object
    # ident = ''
    selected = False ## Whether the mission has been chosen and is active
    hold_for = False  ## Whether the mission has been listed as a possible selection
    task_eligible = False
    route_eligible = False
    task_active = False
    route_active = False
    pending_for = None
    selection_for = None

    def __init__(self, title, details, submitter, task_eligible, route_eligible):
        self.title = title
        self.details = details
        self.submitter = submitter
        self.selected = False
        self.hold_for = None
        self.task_eligible = task_eligible
        self.route_eligible = route_eligible
        self.task_active = False
        self.route_active = False
        self.is_complete = False
        self.pending_for = None
        self.selection_for = None

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
        url_use = url_in.replace('/edit?resourcekey=&gid=', '/export?format=csv&gid=')
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


## SUBMITTED TASKS
 # Reads in the tasks taat are submitted by family members for shuffling and selecting

def build_tasks(target):
    output = {}
    for t in target:
        output[t.id] = t
    with open('tasks.pkl','wb') as f:
        pickle.dump(output, f, protocol=pickle.HIGHEST_PROTOCOL)
    return output
def save_tasks(target):
    with open('tasks.pkl','wb') as f:
        pickle.dump(target, f, protocol=pickle.HIGHEST_PROTOCOL)
    return target

def load_tasks():
    with open('tasks.pkl', 'rb') as f:
        target = pickle.load(f)
    return target
