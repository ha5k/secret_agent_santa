import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
import random
from time import time

sas_gets_present = True  # Toggle whether the secret agent is also part of secret santa
personae_non_grata = []  # List of people not eligible for being the secret agent
is_a_test = input("Type 'y' to confirm this is not a test: ")


# LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES
family, forms, facilitator = sas_utils.load_pickles()
selections = sas_utils.read_form(forms['select_tasks'][1])
responses_expected = len([family[member] for member in family if family[member].playing])  # no. of expected responses


# MAKE SURE YOU HAVE ENOUGH RESPONSES

good_to_go = True
if len(selections.drop_duplicates(subset='Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    print(f"You have responses from {len(selections['Who Are You?'].drop_duplicates())} people")
    names_submitted = selections['Who Are You?'].drop_duplicates().tolist()
    names_to_send = [x for x in list(family) if x not in names_submitted and family[x].playing]

    print("The missing people are:\n\t", '\n\t'.join(names_to_send))

    good_to_go = False
    sas_utils.too_few_responses(selections, forms['select_tasks'][0], family, facilitator)

if len(selections) > responses_expected:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    selections = sas_utils.too_many_responses(selections, family)
    tmp = input('Do you want to override the number of expected responses? (y/n)')
    if tmp == 'y':
        good_to_go = True

if good_to_go:
    print("It's happening. You should be good to go")
    cnfrm = input("Do you want to continue? There's no turning back from here... (y/n)")
    if cnfrm != 'y':
        print("Bailing out!")
        good_to_go = False
    else:
        print("Let's do this! Good luck!")

if good_to_go:

    ## MAKE THE LIST OF TASKS FOR THE SECRET AGENT TO MAKE
    print('Making the task list')
    for member in selections['Who Are You?'].tolist():
        print('\t',member)
        selection = selections.loc[selections['Who Are You?'] == member, 'Which of your tasks do you choose?'].values[0]
        if selection == 'Task A':
            family[member].tasks = [family[member].selections[0]]
            family[member].selections[0].selected = True
        elif selection == 'Task B':
            family[member].tasks = [family[member].selections[1]]
            family[member].selections[1].selected = True
        elif selection == 'Task C':
            family[member].tasks = [family[member].selections[2]]
            family[member].selections[2].selected = True
        elif selection == 'I am Feeling Lucky':

        else:
            print('Something weird is up with task selection for ', member)
            family[member].tasks = [family[member].selections[2]]
            family[member].selections[2].selected = True

    # Make sure you reset old results if needed
    for member in family:
        family[member].is_agent = False

    print("Let's make some pairings!")
    good_solution = False
    while not good_solution:
        gifters = [x for x in list(family)]  # Make a list of all the people in the game
        random.shuffle(gifters)

        # Select the secret agent, separate them if needed
        sas = gifters[0]

        # Make sure the SAS is up for the task
        if sas not in personae_non_grata and family[sas].playing:
            good_solution = True
            family[sas].is_agent = True
            # If SAS is out of gift exchange, remove them
            if not sas_gets_present:
                gifters = [x for x in gifters[1:]]

    # Assign tasks to the Secret Agent
    for member in family:
        if not family[member].is_agent and family[member].playing:
            family[sas].tasks.append(family[member].tasks[0])

    # Make the pairings
    good_solution = False
    while not good_solution:
        random.shuffle(gifters)

        #Assign each person the next person in the list
        results = {}
        for k in range(len(gifters)):
            family[gifters[k]].gives_to = gifters[(k+1)%len(gifters)]
        good_solution = True
        for member in family:
            if family[member].gives_to == family[member].partner:
                print('Broken Pair, Try Again')
                good_solution = False
                break
    print('You did it!')
    ## Save a copy of the family pickle with task information
    with open('family.pkl','wb') as f:
        pickle.dump(family, f)


