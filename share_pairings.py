import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
import random
from time import time

sas_gets_present = True #Toggle whether the secret agent is also part of secret santa
personae_non_grata = ['Mom', 'Dad', 'Peggy', 'David'] #List of people not eligible for being the secret agent
set_seed = 10


## LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES
family, forms, facilitator = sas_utils.load_pickles()
submissions = sas_utils.read_form(forms['select_tasks'][1])
responses_expected = len(family) #number of people you were expecting to have responded


## MAKE SURE YOU HAVE ENOUGH RESPONSES

good_to_go = True
if len(submissions.drop_duplicates(subset='Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    good_to_go = False
    sas_utils.too_few_responses(submissions, forms['select_tasks'][0], family, facilitator)

if len(submissions) > responses_expected:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    submissions = sas_utils.too_many_responses(submissions, family)
    tmp = input('Do you want to override the number of expected responses? (y/n)')
    if tmp == 'y':
        good_to_go = True

if good_to_go:

    ## MAKE THE LIST OF TASKS FOR THE SECRET AGENT TO MAKE
    print('Making the task list')
    with open('shuffled_tasks.pkl', 'rb') as f:
        all_tasks = pickle.load(f)

    vetted_tasks = submissions.copy().drop_duplicates(subset = 'Who Are You?', keep = 'last') #Drop extra submissions

    use_tasks = {}
    for row in vetted_tasks.iterrows():
        name = row[1].values[1]
        selection = row[1].values[2]
        if selection == 'Task A':
            use_task = 'st1'
        elif selection == 'Task B':
            use_task = 'st2'
        elif selection == 'Task C':
            use_task = 'st3'
        else:
            print('Something happened with your task selection process. Assuming Task A')
            use_task = 'st1'

        use_tasks[name] = all_tasks.loc[all_tasks['Who Are You?'] == name, use_task].values[0]
        # append([all_tasks.loc[all_tasks['Who Are You?'] == name, use_task].values[0],name])

    print("Let's make some pairings!")

    # random.seed(set_seed)
    good_solution = False
    while not good_solution:
        gifters = [x for x in list(family)] #Make a list of all the people in the game
        random.shuffle(gifters)

        #Select the secret agent, separate them if needed
        sas = gifters[0]

        #Make sure the SAS is up for the task
        if sas not in personae_non_grata:
            good_solution = True

    #Make the pairings
    good_solution = False
    while not good_solution:
        random.shuffle(gifters)

        #Assign each person the next person in the list
        results = {}
        for k in range(len(gifters)):
            results[gifters[k]] = (gifters[(k+1)%len(gifters)], gifters[k] == sas)

        #Check to make sure the pairings are good
        good_solution = True
        for giver in gifters:
            if results[giver][0] == family[giver][1]:
                good_solution = False
                print('Broken Pair, Try Again')
                break

    ## SHARE THE TASKS AND THE INFO FOR THE SECRET AGENT

    sas_gifting_msg = "Remember, the Secret Agent this year IS NOT part of secret santa. They don't get or give a gift."
    if sas_gets_present:
        sas_gifting_msg = 'Remember, the Secret Agent this year IS part of secret santa. They get and give a gift.'

    sas_task_string = 'You ARE the Secret Agent. Your mission objectives are ' \
                      'as follows:\n'+'\n'.join(['\t-'+use_tasks[k] for k in use_tasks])

    print('Formatting and sending emails...')
    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        for giver in results:

            receiver = results[giver][0]
            is_sas = results[giver][1]

            if is_sas: #Giver is the secret agent. Their tasks need to be a list
                task_string = sas_task_string
                preface = 'Time to work on your poker face because...'
                if sas_gets_present:
                    preface = f'You have been randomly assigned to get a present for {receiver}\n\nAlso...'+preface
            else:
                task_string = 'You are NOT the Secret Agent, but still have to ' \
                              'complete the mission you selected:\n\t-'+use_tasks[giver]
                preface = f'You have been randomly assigned to get a present for {receiver}\n\nAlso...'

            message = '\n'.join([

                'Subject: {}\n\n'.format('Your SECRET Secret Agent Santa Results'), #todo fix the subject to break conversations


                f"Hey there, {giver}\n",
                'Get excited, your Secret Agent Santa tasks are ready! '+sas_gifting_msg,
                '',
                preface,
                task_string,
                '',
                'HO HO HO,',
                'Your Secret Agent Santa Bot'
            ])
            server.sendmail(facilitator['email'], family[giver][0],
                            message.replace('\u2019', '"').replace('\u201c', '"').replace('\u201d', '"'))

            print(f'\t...sent to {giver} at {family[giver][0]}')




