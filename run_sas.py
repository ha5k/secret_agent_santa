### This script is designed to run everything else as a single function.
 # Every script runs as an import and saves data as a pkl... for some reason

import sas_utils
import pickle
family, forms, facilitator = sas_utils.load_pickles()

# If game hasn't started, send out the first batch of emails
if facilitator['game_state'] == 'Not Started':
    print('Emailing to Request Submissions')
    exec(open('email_request_submissions.py').read())

elif facilitator['game_state'] == 'Get Submissions':
    print('Pulling submissions and requesting selections')
    exec(open('shuffle_submissions.py').read())

elif facilitator['game_state'] == 'Shuffled submissions':
    print('Requesting Selections')
    import email_request_selections
    exec(open('email_request_selections.py').read())

elif facilitator['game_state'] == 'Get Selections':
    print('Pulling selections and starting the game')
    import build_assignments
    exec(open('build_assignments.py').read())
    import email_issue_tasks
    exec(open('email_issue_tasks.py').read())

elif facilitator['game_state'] == 'Run Game':
    print('Running the game')
    import draw_route_cards
    print('Checking for Route Requests')
    exec(open('draw_route_cards.py').read())
    import select_route_cards
    print('Checking for Route Selections')
    exec(open('select_route_cards.py').read())
    import run_messages
    print('Checking for Messages')
    exec(open('run_messages.py').read())

with open('facilitator_details.pkl', 'wb') as f:
    pickle.dump(facilitator, f)
