import pandas as pd
import smtplib
import ssl
import pickle

with open('test.pkl', 'rb') as file:
    vars = pickle.load(file)
port = vars[0]
password = vars[1]


smtp_server = "smtp.gmail.com"
sender_email = "kylesgonnahatethis@gmail.com"  # Enter your address
receiver_email = "eamonn.shirey@gmail.com"  # Enter receiver address
message = """\
Subject: Hi there

This message is sent from Python."""

context = ssl.create_default_context()
with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, receiver_email, message)
