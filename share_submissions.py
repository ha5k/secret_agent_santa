import pandas as pd
import smtplib
import pickle
import numpy as np

reponses_expected = 8 #number of people you were expecting to have responded

## LOAD IN FAMILY AND FORM INFORMATION, THEN READ IN RESPONSES

family, forms, facilitator = sas_utils.load_pickles()
submissions = sas_utils.read_form(forms['submit_tasks'][1])

## CHECK THE NUMBER OF RESPONSES IN THE GOOGLE FORM

good_to_go = True
if len(submissions.drop_duplicates(subset = 'Who Are You?')) < responses_expected:
    print("You're missing responses from someone in the family")
    good_to_go = False
    send_reminder = input('You want me to send a reminder email? (y/n)')

    if send_reminder == 'y':
        responder_names = submissions['Who Are You?'].tolist()

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(facilitator['email'], facilitator['pwd'])


            for member in family:
                if responder_names.count(member) <= 0:
                    message = '\n\n'.join([
                        f'Hey there {member}',
                        "It looks like like you haven't submitted tasks for Secret Agent Santa.",
                        "You wouldn't want to be put on the naughty list, would you?",
                        f'Please submit your tasks here:\n{forms[submit_tasks][0]}',
                        "If you have any questions, get in touch with Eamonn! He can help!",
                        "Please advise,\nYour Secret Agent Santa Bot"
                    ])
                    server.sendmail(faciliator['email'], family[member]['email'], message)

if len(submissions) > responses_expected:
    print('You have too many responses. Time to panic!')
    print('But seriously, you can probably make it work if you get more details from folks')
    print('Follow up to make sure their most recent submission is the one they want to use')
    good_to_go = False

    responder_names = submissions['Who Are You?'].tolist()
    for member in family:
        if responder_names.count(member) >= 1:
            print(f'\t{member} is duplicated')

    cont = input('Want to continue with the most recent submissions? (y/n)')
    if cont == 'y':
        submissions.drop_duplicates(subset = 'Who Are You?', keep = 'last', inplace = True)
        if len(submissions) == responses_expected:
            good_to_go = True



## SHUFFLE THE TASKS SO NO ONE GETS THEIR OWN (IF GOOD TO GO AHEAD)

if good_to_go:

    well_shuffled = False
    while not well_shuffled:
        jumble = submissions.copy()
        for k in ['1','2','3']:
            jumble['st'+k] = [x for x in submissions['Secret Task '+k].tolist().shuffle()]

        jumble['dupes'] = np.where((jumble['Secret Task 1' ] == jumble.st1) |
                                   (jumble['Secret Task 2' ] == jumble.st2) |
                                   (jumble['Secret Task 3' ] == jumble.st3),
                                   1,0)
        if jumble.dupes.sum() == 0:
            well_shuffled = True

    # Save a full copy of the submissions for later review
    with open('shuffled_tasks.pkl') as f:
        pickle.dump(jumble, f)

## SHARE THE SUBMISSIONS AND ASK FOR SELECTIONS

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        for row in jumble.iterrows():
            message = '\n'.join([
                f"Greetings, {row[1]['Who Are You?']}\n",
                "It's time for you to select your Secret Agent Santa task. The Secret Agent will receive your selection as one of their tasks.\n",
                "Remember, for the task to count, YOU have to do whatever task you select. So choose wisely.\n",
                "The tasks you can choose from are:",
                f"\tTask A: {row[1].st1}",
                f"\tTask B: {row[1].st2}",
                f"\tTask C: {row[1].st3}\n",
                "Please make your selection here:",
                forms['select_tasks'][0]+'\n',
                'Best of Luck,',
                'Your Secret Agent Santa Bot'
            ])
            server.sendmail(faciliator['email'], family[row[1]['Who Are You?']]['email'], message)






