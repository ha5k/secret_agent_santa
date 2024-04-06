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
    - 