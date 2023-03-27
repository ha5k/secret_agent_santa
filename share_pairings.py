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


if len(submissions) > responses_expected: