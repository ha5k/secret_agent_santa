import pandas as pd
import smtplib
import pickle
import numpy as np

reponses_expected = 8 #number of people you were expecting to have responded

## LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES

family, forms, facilitator = sas_utils.load_pickles()
submissions = sas_utils.read_form(forms['select_tasks'][1])

## MAKE SURE YOU HAVE ENOUGH RESPONSES

good_to_go = True
if len(submissions.drop_duplicates(subset = 'Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    good_to_go = False
    sas_utils.too_few_responses(submissions, forms['select_tasks'][0], family, facilitator)

if len(submissions) > responses_expected:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    submissions = sas_utils.too_many_responses(submissions, family)
    if len(submissions) == responses_expected:
        good_to_go = True

if good_to_go:
