

import random
import smtplib



# Ask each person to submit a task
tasks = {}
for name, email in family.items():
    task = input(f'Hi {name}, please enter a task for the person without a partner: ')
    tasks[name] = task

# Shuffle the list of names to ensure random pairings
names = list(family.keys())
random.shuffle(names)

# Remove one person from the list of names
no_partner = random.choice(names)
names.remove(no_partner)

# Create a dictionary to hold the pairings
pairings = {}

# Loop through the shuffled list of names and assign each person to the next person in the list (wrapping around to the beginning if necessary),
# making sure they are not paired with their spouse
for i in range(len(names)):
    giver = names[i]
    receiver = names[(i + 1) % len(names)]
    while family.get(giver) == receiver or family.get(receiver) == giver:
        # If the giver and receiver are spouses, reassign the receiver
        receiver = names[(names.index(receiver) + 1) % len(names)]
    pairings[giver] = receiver

# If there is no partner for one person, assign them the task submitted by each person
if no_partner:
    task_list = '\n'.join(tasks.values())
    pairings[no_partner] = task_list

# Send an email to each person with their assigned gift recipient or task list
smtp_server = 'smtp.example.com'  # Replace with your SMTP server
smtp_port = 587  # Replace with your SMTP port
smtp_username = 'your_username'  # Replace with your SMTP username
smtp_password = 'your_password'  # Replace with your SMTP password

for giver, recipient in pairings.items():
    sender_email = family[giver]
    if type(recipient) == str:
        # If the recipient is a task list, format the email message accordingly
        message = f'Subject: Secret Santa\n\nHi {giver},\n\nUnfortunately, we were unable to pair you up with anyone for this year\'s Secret Santa gift exchange. Instead, you have been assigned the following tasks:\n\n{recipient}\n\nBest regards,\nYour Secret Santa Bot'
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, sender_email, message)
    else:
        # If the recipient is a person, format the email message accordingly
        message = f'Subject: Secret Santa\n\nHi {giver},\n\nYou have been assigned to buy a gift for {recipient}. Happy holidays!\n\nBest regards,\nYour Secret Santa Bot'
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, family[recipient], message)
