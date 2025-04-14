### This script is designed to run everything else as a single function.
 # Every script runs as an import and saves data as a pkl... for some reason

import sas_utils
family, forms, facilitator = sas_utils.load_pickles()

# If game hasn't started, send out the first batch of emails
if facilitator['game_state'] == 'Not Started':
    print('Emailing to Request Submissions')
    # import email_request_submissions
    exec(open('email_request_submissions.py').read())
    facilitator['game_state'] = 'Get Submissions'

elif facilitator['game_state'] == 'Get Submissions':
    import shuffle_submissions
    exec(open('shuffle_submissions.py').read())
    import email_request_selections
    exec(open('email_request_submissions.py').read())

elif facilitator['game_state'] == 'Get Selections':
    import build_assignments
    exec(open('build_assignments.py').read())
    import email_issue_tasks
    exec(open('email_request_submissions.py').read())

elif facilitator['game_state'] == 'Run Game':
    import draw_route_cards
    exec(open('draw_route_cards.py').read())
    import select_route_cards
    exec(open('select_route_cards.py').read())
    import run_messages
    exec(open('run_messages.py').read())




