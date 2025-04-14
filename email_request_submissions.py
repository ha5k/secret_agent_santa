import smtplib
import sas_utils
from sas_utils import person
from time import time

if __name__ == "__main__":

    ## LOAD IN FAMILY AND FORM INFORMATION
    family, forms, facilitator = sas_utils.load_pickles()
    is_a_test = facilitator['is_test']

    ## SEND LINK TO SUBMIT TASKS
    print('Opening Email Connection...')
    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        print('Connection Opened!')
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])
        subject = f'Subject: Submit your tasks for Secret Agent Santa!'
        if is_a_test:
            subject = f'Subject: Submit your tasks for the TEST Secret Agent Santa! ({round(time())})'
        for member in family:
            if family[member].playing:
                print('\tWorking on: '+member)
                message = '\n\n'.join([subject,
                                       f'Hi {member}',
                                       f'Please submit three tasks for the 2025 Edition of Secret Agent Santa at the following link:',
                                       forms['submit_tasks'][0],
                                       'Cheers,\nYour Secret Agent Santa Bot'
                                       ])
                server.sendmail(facilitator['email'], family[member].email, message)
            else:
                print('\tSkipping ' + member + " because they're lame")
        print('Done requesting submissions!')

        facilitator['game_state'] = 'Get Selections'
        with open('facilitator_details.pkl','wb') as f:
            pickle.dump(facilitator, f)

