

import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle



## LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES

family, forms, facilitator = sas_utils.load_pickles()
submissions = sas_utils.read_form(forms['submit_tasks'][1])
responses_expected = len(family) #number of people you were expecting to have responded
is_a_test = input("Type 'y' to confirm this is not a test: ")

## CHECK THE NUMBER OF RESPONSES IN THE GOOGLE FORM

good_to_go = True
if len(submissions.drop_duplicates(subset = 'Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    good_to_go = False
    sas_utils.too_few_responses(submissions, forms['submit_tasks'][0], family, facilitator)

if len(submissions) > responses_expected:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    submissions = sas_utils.too_many_responses(submissions, family)
    if len(submissions) == responses_expected:
        good_to_go = True



## SHUFFLE THE TASKS SO NO ONE GETS THEIR OWN (IF GOOD TO GO AHEAD)

if good_to_go:

    well_shuffled = False
    print('Shuffling Tasks...')
    while not well_shuffled:
        print('Shuffle!')
        jumble = submissions.copy()
        # tasks = [x for x in submissions['Secret Task']]
        for k in ['1','2','3']:
            print('\tAssign!',k)
            jumble['st'+k] = [x for x in submissions['Secret Task '+k].sample(frac=1).tolist()]
            # jumble['st' + k] = [x for x in submissions['Secret Task ' + k].tolist()]

        jumble['dupes'] = np.where((jumble['Secret Task 1' ] == jumble.st1) |
                                   (jumble['Secret Task 2' ] == jumble.st2) |
                                   (jumble['Secret Task 3' ] == jumble.st3),
                                   1,0)
        if jumble.dupes.sum() == 0:
            well_shuffled = True
            print('Good Shuffle!')

    # Save a full copy of the submissions for later review
    with open('shuffled_tasks.pkl','wb') as f:
        pickle.dump(jumble, f)

## SHARE THE SUBMISSIONS AND ASK FOR SELECTIONS

    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        subject = 'Subject: {}\n\n'.format('Select your Secret Agent Santa Task')
        if is_a_test != 'y':
            subject = 'Subject: {}\n\n'.format('Select your TEST Secret Agent Santa Task ('+str(round(time()))+')')
        for row in jumble.iterrows():
            print('Sending message to: '+row[1]['Who Are You?'])
            message = '\n'.join([
                subject,
                f"Greetings, {row[1]['Who Are You?']}\n",
                "It's time for you to select your Secret Agent Santa task. The Secret Agent will receive your selection as one of their tasks.\n",
                "Remember, for the task to count, YOU have to do whatever task you select. Choose wisely.\n",
                "The tasks you can choose from are:",
                f"\tTask A: {row[1].st1}",
                f"\tTask B: {row[1].st2}",
                f"\tTask C: {row[1].st3}\n",
                "Please make your selection here:",
                forms['select_tasks'][0]+'\n',
                'Best of Luck,',
                'Your Secret Agent Santa Bot'
            ])
            server.sendmail(facilitator['email'], family[row[1]['Who Are You?']][0],
                            message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'"))
            # TODO This unicode replacement is rough. Consider fixing.






