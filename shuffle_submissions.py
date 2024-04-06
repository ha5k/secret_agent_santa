

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

responses_expected = len([family[member] for member in family if family[member].playing])  # no. of expected responses
is_a_test = input("Type 'y' to confirm this is not a test: ")

## CHECK THE NUMBER OF RESPONSES IN THE GOOGLE FORM

good_to_go = True

## Check whether you're short on people
if len(submissions.drop_duplicates(subset = 'Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    print(f"You have responses from {len(submissions['Who Are You?'].drop_duplicates())} people")

    names_submitted = submissions['Who Are You?'].drop_duplicates().tolist()
    names_to_send = [x for x in list(family) if x not in names_submitted and family[x].playing]

    print("The missing people are:\n\t", '\n\t'.join(names_to_send))

    good_to_go = False
    sas_utils.too_few_responses(submissions, forms['submit_tasks'][0], family, facilitator)

else:
    print('You have enough people!')

## Check whether you have too many responses
if len(submissions) > responses_expected and good_to_go:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    submissions = sas_utils.too_many_responses(submissions, family)
    if len(submissions) == responses_expected:
        good_to_go = True

## Merge tasks from form back into the family pickle
if good_to_go:
    all_submissions = []
    for member in family:
        if len(family[member].submissions) != 0:
            input('Member %s already has tasks submiitted. You sure you are good to overwrite?' % family[member].name)
    for n in submissions['Who Are You?'].tolist():
        print('Gathering Submissions from ', n)
        s = submissions.loc[submissions['Who Are You?'] == n, ['Secret Task 1', 'Secret Task 2', 'Secret Task 3']].values.flatten().tolist()
        all_submissions += s
        family[n].submissions = s
    for member in family:
        if len(family[member].submissions) != 3:
            input('Something is up with %s and their tasks' % family[member].name)

    ## Shuffle the tasks so no one gets their own
    success = False
    while not success:
        success = True
        temp_submits = [k for k in all_submissions]
        shuffle(temp_submits)
        for member in family:
            k = 0
            temp_selects = []
            while len(temp_selects) < 3:
                if temp_submits[k] not in family[member].submissions:
                    temp_selects.append(temp_submits.pop(k))
                else:
                    k += 1
                if len(temp_submits) <= k and len(temp_selects) <3:
                    success = False
                    print('FAIL! Restarting')
                    for m in family:
                        family[m].selections = []
                    break
            family[member].selections = temp_selects

    ## Save a copy of the family pickle with task information
    with open('family.pkl','wb') as f:
        pickle.dump(family, f)

