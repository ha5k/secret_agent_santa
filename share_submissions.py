import pandas
import smtplib
import pickle

## LOAD IN FAMILY AND FORM INFORMATION

with open('family_details.pkl','r') as f:
    family = pickle.load(f)
with open('form_details.pkl','r') as f:
    forms = pickle.load(f)
with open('facilitator_details.pkl', 'r') as f:
    facilitator = pickle.load(f)
