import smtplib
import sas_utils
from random import shuffle

## Enter the relevant information below
celeb = 'Jen Polan'
celeb_email = 'jenpolan@gmail.com'
target = 'Jenn'
send_email = True

family, forms, facilitator = sas_utils.load_pickles()

tasks = family[target].submissions
shuffle(tasks)

selection_title = ''
selection_details = ''
for t in tasks:
    selection_title = t.title
    selection_details = t.details
    if not t.selected:
        break

print(f'Sending message to: {celeb}, {celeb_email}')

subject = 'Subject: {}\n\n'.format('Your Secret Agent Santa Celebrity Shot')
message = '\n'.join([
    subject,
    f"Hey there, {celeb} - \n",
    "Thanks for your interest in trying out a Secret Agent Santa celebrity shot.\n",
    ("Remember, we've never done this before, so we're kind of flying blind. Below, you'll find a task name and "
     "details, but the catch is that you can't tell Eamonn about them. Or anyone really."),
    ("That means if something seems off or wrong, you can't share too many details about it. Anything that would "
     "speak to the nature of the task is off limits!\n"),
    "You can, however, give Eamonn a shout and he'll try his best to fix it.\n"

    f"Your celebrity shot comes from {target}, and is as follows:",

    f"\nTask: {selection_title}",
    f"{selection_details}\n",

    ("If you choose not to do the task, it's no harm no foul. If you do the task, make sure you document it "
     "and let Eamonn know so he can work you into the ceremony at year's end."),

    '\nBest of Luck,',
    'The Secret Agent Santa Bot'
])

if send_email:
    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
        server.starttls()
        server.login(facilitator['email'], facilitator['pwd'])
        server.sendmail(facilitator['email'], celeb_email,
                        message.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2018',
                                                                                                             "'").replace
                        ('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace("\u2026", '...'))