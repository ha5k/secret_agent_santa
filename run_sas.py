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
    import email_request_selections

elif facilitator['game_state'] == 'Get Selections':
    import build_assignments
    import email_issue_tasks

elif facilitator['game_state'] == 'Run Game':
    import draw_route_cards
    import select_route_cards
    import run_messages




