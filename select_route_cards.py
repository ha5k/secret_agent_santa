
import pandas as pd
import smtplib
import pickle
import numpy as np
import sas_utils
from time import time
from random import shuffle

if __name__ == "__main__":

    ## Read In Form for Drawing Route Cards
    family, forms, facilitator = sas_utils.load_pickles()
    route_selections = sas_utils.read_form(forms['select_routes'][1])

    sas_routes = []
    for member in route_selections['Secret Code'].tolist():
            if len(family[member].tasks) == 0 and family[member].playing:
                print('Someone selected Route Cards!')
                selection = route_selections.loc[route_selections['Secret Code'] == member, 'Which of your tasks do you choose?'].values[0]

                if selection == 'Task A':
                    family[member].tasks = [family[member].selections[0]]
                    family[member].selections[0].selected = True
                    sas_routes.append(family[member].selections[0])

                elif selection == 'Task B':
                    family[member].tasks = [family[member].selections[1]]
                    family[member].selections[1].selected = True
                    sas_routes.append(family[member].selections[1])

                elif selection == 'Task C':
                    family[member].tasks = [family[member].selections[2]]
                    family[member].selections[2].selected = True
                    sas_routes.append(family[member].selections[2])

                else:
                    # print('Something weird is up with task selection for ', member)
                    family[member].tasks.append([family[member].selections[2]])
                    family[member].selections[2].selected = True
                    sas_routes.append([family[member].selections[2]])

    # Add task to the secret agent's list
    for member in family:
        if family[member].is_agent:
            family[member].tasks += sas_routes

    # Email confirmation to the chooser
    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])

        sas = [k for k in family if family[k].is_agent][0]
        for member in family:
            if not family[member].task_emailed and not family[member].is_agent and family[member].playing:
                subject = 'Subject: {}\n\n'.format('Your Secret Agent Santa Bonus Route Confirmation')
                message = '\n'.join([
                    subject,
                    f"Hey there, {member.split('_')[0]}\n",
                    "Congrats! You chose more tasks! Good luck with that.\n",
                    "The additional task you chose is:",
                    family[member].tasks[0].title + '\n'+ family[member].tasks[0].details,
                    "\nBest of luck...",
                    "Kringle. Kris Kringle"
                    ])
                server.sendmail(facilitator['email'], family[member].email,
                                message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                    '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                    "\u2026", '...'))
                family[member].task_emailed = True

                server.sendmail(facilitator['email'], family[member].email,
                            message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                "\u2026", '...'))


                subject = 'Subject: {}\n\n'.format('Someone Drew a Route Card...')
                message = '\n'.join([
                    subject,
                    f"Hey there, {sas}\n",
                    "I'm sorry to report that someone drew a route card. So now you have an extra task...\n",
                    "Your new list of tasks is:",
                    '\n ' + '\n'.join(['\n' + task.title + '\n' + task.details for task in family[sas].tasks]),
                    "\nBest of luck..."
                    "Kringle. Kris Kringle"
                ])
                server.sendmail(facilitator['email'], family[sas].email,
                                message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                    '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                    "\u2026", '...'))

                subject = 'Subject: {}\n\n'.format('Someone Drew a Route Card...')
                message = '\n'.join([
                    subject,
                    f"THISISSECRETTHISISSECRETTHISISSECRETTHISISSECRETTHISISSECRETTHISISSECRETTHISISSECRETTHISISSECRET\n, {sas}\n",
                    "I'm sorry to report that someone drew a route card. So now you have an extra task...\n",
                    "Your new list of tasks is:",
                    '\n ' + '\n'.join(['\n' + task.title + '\n' + task.details for task in family[sas].tasks]),
                    "\nBest of luck..."
                    "Kringle. Kris Kringle"
                ])
                server.sendmail(facilitator['email'], 'asai.secret.agent.santa@gmail.com',
                                message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                    '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                    "\u2026", '...'))

            elif family[member].playing:
                subject = 'Subject: {}\n\n'.format('Someone Drew a Route Card...')
                message = '\n'.join([
                    subject,
                    f"Hey there, {member}\n",
                    "I just wanted to let you know that someone just chose a route card.",
                    "Be on the lookout for renewed shenangigans, suspicious behavior, or sudden attempts to connect LA and NYC.",
                    "\nAll Aboard!",
                    "Uncanny Valley Tom Hanks",
                    "(The conductor of the Polar Express)"
                ])
                server.sendmail(facilitator['email'], family[member].email,
                                message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                    '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                    "\u2026", '...'))


    ## Save the new pickle file
    with open('family.pkl', 'wb') as f:
        pickle.dump(family, f)
