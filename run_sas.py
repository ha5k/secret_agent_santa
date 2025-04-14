### This script is designed to run everything else as a single function.

import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

family, forms, facilitator = sas_utils.load_pickles()

# If game hasn't started, send out the first batch of emails
if facilitator['game_state'] == 'Not Started':
    import email_request_submissions
    facilitator['game_state'] = 'Get Submissions'

elif facilitator['game_state'] == 'Get Submissions':
    import shuffle_submissions
    import email_request_selections
    facilitator['game_state'] == 'Get Selections'

elif facilitator['game_state'] == 'Get Selections':
    import build_assignments
    facil



