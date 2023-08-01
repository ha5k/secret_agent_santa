import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
import random

sas_gets_present = True #Toggle whether the secret agent is also part of secret santa
personae_non_grata = ['Mom','Dad'] #List of people not eligible for being the secret agent
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

    tasks = []
    for row in vetted_tasks.iterrows():
        name = row[1].values[0]
        selection = row[1].values[1]


        tasks.append(all_tasks.loc[all_tasks['Who Are You?'] == f, submissions])

    print("Let's make some pairings!")

    # random.seed(set_seed)
    good_solution = False
    while not good_solution:
        gifters = [x for x in list(family)] #Make a list of all the people in the game
        random.shuffle(gifters)

        #Select the secret agent, separate them if needed
        if sas_gets_present:
            sas = gifters[0]
        else:
            sas = gifters.pop(0)

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
                print('Broken Pair: %s got %s'%(giver, results[giver][0]))
                break





    ## SHARE THE SUBMISSIONS AND ASK FOR SELECTIONS

    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        for row in jumble.iterrows():
            message = '\n'.join([
                f"Greetings, {row[1]['Who Are You?']}\n",
                "It's time for you to select your Secret Agent Santa task. The Secret Agent will receive your selection as one of their tasks.\n",
                "Remember, for the task to count, YOU have to do whatever task you select. Choose wisely.\n",
                "The tasks you can choose from are:",
                f"\tTask A: {row[1].st1}",
                f"\tTask B: {row[1].st2}",
                f"\tTask C: {row[1].st3}\n",
                "Please make your selection here:",
                forms['select_tasks'][0] + '\n',
                'Best of Luck,',
                'Your Secret Agent Santa Bot'
            ])
            server.sendmail(facilitator['email'], family[row[1]['Who Are You?']]['email'], message)






