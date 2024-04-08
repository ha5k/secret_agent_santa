# secret_agent_santa
Code relating to running the (hopefully) annual secret agent santa project


Order of Operations:
1) Set up the pickle_jar file:
    a) Ensure the family dict is up to date with participants and emails
    b) Build the google forms and response urls in the forms dict
    c) Run it
2) Run email_request_submissions.py
    - This will send emails to all your participants
3) Run shuffle_submissions.py
    - This will let you send reminders if not everyone has responded
    - Will help clean up results if people responded multiple times
    - Will shuffle tasks and assign them to each participant for consideration
4) Run email_request_selections.py
    - This will email participants their selections, from which they choose one
5) Run build_assignments.py
    - This will Connect each participant's task selection to the task
    - Will assign a secret agent
    - will give each secret santa someone to gift to
6) Run email_issue_tasks.py
    - This shares final tasks and gift assignments