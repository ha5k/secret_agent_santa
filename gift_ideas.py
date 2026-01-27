import smtplib
import pandas as pd
import sas_utils
import pickle

def build_gift_facilitator():
    idea_count = 0
    req_count = 0
    msg_count = 0

    with open('gift_facilitator_details.pkl', 'wb') as f:
        pickle.dump({'idea_count': idea_count, 'req_count': req_count, 'msg_count': msg_count},
                    f, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == "__main__":

    family, forms, facilitator = sas_utils.load_pickles()
    try:
        with open('gift_facilitator_details.pkl', 'rb') as f:
            gift_facilitator = pickle.load(f)
    except:
        gift_facilitator = build_gift_facilitator()

    link_ideas = 'https://docs.google.com/spreadsheets/d/1IBcVRAxrMf2wP_gkJeZBObLuRuarUIEoHQcvdoEgu4E/edit?resourcekey=&gid=206401127#gid=206401127'
    link_requests = 'https://docs.google.com/spreadsheets/d/1IBcVRAxrMf2wP_gkJeZBObLuRuarUIEoHQcvdoEgu4E/edit?resourcekey=&gid=1254355179#gid=1254355179'
    link_messages = 'https://docs.google.com/spreadsheets/d/1IBcVRAxrMf2wP_gkJeZBObLuRuarUIEoHQcvdoEgu4E/edit?resourcekey=&gid=1422697416#gid=1422697416'

    ## import dataframes from links
    ideas = sas_utils.read_form(link_ideas)
    requests = sas_utils.read_form(link_requests)
    gift_messages = sas_utils.read_form(link_messages)

    ideas_from = ideas["What's your name?"].drop_duplicates().tolist()
    ideas['id'] = [(k*7) + 100 for k in range(len(ideas))] ## Make the id count look somewhat random


    ## Handle the gift idea requests
    if len(requests) > gift_facilitator['req_count']: ## You have new requests
        print('There are new gift requests!')
        k = 0
        for r in requests.iterrows():
            ask_for_help = False
            if k >= gift_facilitator['req_count']:

                giver = r[1]['Who are you? ']
                receiver = family[giver].gives_to

                subject = 'Subject: {}\n\n'.format('You requested Secret Santa gift ideas!')
                message = "I'm sorry, but I can't let you do that. You need to submit a gift idea before you can receive a gift idea.\n\n You can do that here: https://forms.gle/5VTc3KNDWpNNY3ER9\n\nAdd something, then make another request!"
                if giver in ideas_from: # They've given a gift idea, so they can get ideas
                    tmp_ideas = ideas.loc[ideas['Who is the gift for?'] == receiver].copy()

                    message = "You asked for gift ideas for %s! They're below.\n\n" % receiver
                    gift_list = tmp_ideas["What's the gift idea?"].tolist()
                    details_list = tmp_ideas["Any more details? "].tolist()
                    id_list = tmp_ideas['id'].tolist()

                    if len(id_list) == 0:
                        message = "I'm sorry - no one has submitted ideas for this person yet. Check back later."
                        ask_for_help = True

                    else:
                        for foo in range(len(gift_list)):
                            addendum = 'ID'+str(id_list[foo]) + ': ' + gift_list[foo] + '\n' + details_list[foo] + '\n\n'
                            message += addendum


                to_send = subject + message + '\n\nCheers,\nThe SAS Bot'
                # print(to_send)
                with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
                    server.starttls()
                    server.login(facilitator['email'], facilitator['pwd'])
                    server.sendmail(facilitator['email'], family[giver].email,
                                to_send.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                    '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                    "\u2026", '...'))

                if ask_for_help:
                    partner = family[receiver].partner

                    subject_2 = 'Subject: {}\n\n'.format('Secret Agent Santa needs your help!')
                    message_2 = 'Hey!\nSomeone is looking for gift ideas for %s. ' % receiver
                    message_2 += "If you have any ideas, can you submit them here?\n https://forms.gle/43HdqfigBw7RK92L9"
                    message_2 += '\n\nThanks,\nThe SAS Bot'

                    to_send_2 = subject_2 + message_2

                    # print(to_send_2)
                    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
                        server.starttls()
                        server.login(facilitator['email'], facilitator['pwd'])
                        server.sendmail(facilitator['email'], family[partner].email,
                                    to_send_2.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                        '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                        "\u2026", '...'))


            k += 1

    ## Handle the gift messages
    if len(gift_messages) > gift_facilitator['msg_count']: ## You have new messages
        print('There are new gift messages!')
        k = 0
        for r in gift_messages.iterrows():
            if k >= gift_facilitator['msg_count']:
                # print(k)
                gift_number = r[1]['What gift number is this about? ']


                if gift_number in ideas.id.to_list():
                    gift_title = ideas.loc[ideas['id'] == gift_number, "What's the gift idea?"].values[0]
                    msg_txt = r[1]["What's your message?"]

                    idea_from = ideas.loc[ideas['id'] == gift_number]["What's your name?"].values[0]
                    receiver = ideas.loc[ideas['id'] == gift_number]["Who is the gift for?"].values[0]

                    giver = ''
                    for person in family:
                        if family[person].gives_to == receiver:
                            giver = person
                            break

                    message = "You have a new message about a gift idea for idea number %s. You might have sent the message, but either way you can respond here:\n" % gift_number
                    message += "https://forms.gle/3BY8uiJcWdQRK5su8\n\n"
                    message += "The gift idea was number %s" % gift_number +": "+ gift_title +"\n\n"
                    message += "The message is as follows:\n"+msg_txt

                else:
                    message = "You asked to send a message about a gift idea. But the task id you mentioned isn't a task. You can try again, though!"
                    giver = ''
                    idea_from = ''
                message += "\n\nCheers,\nSAS Bot"

                subject = 'Subject: {}\n\n'.format('You have a message about Secret Santa gift ideas! #%s'%gift_number)
                to_send = subject + message

                for member in [giver, idea_from]:
                    if member == '':
                        break
                    # print(k,member, giver, idea_from)
                    # print(to_send)
                    with smtplib.SMTP('smtp.gmail.com', facilitator['port']) as server:
                        server.starttls()
                        server.login(facilitator['email'], facilitator['pwd'])
                        server.sendmail(facilitator['email'], family[member].email,
                                    to_send.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace(
                                        '\u2018', "'").replace('\u2013', '-').replace('\xe9', "[e-with-an-accent]").replace(
                                        "\u2026", '...'))
            k+=1

    with open('gift_facilitator_details.pkl', 'wb') as f:
        pickle.dump({'idea_count': len(ideas), 'req_count': len(requests), 'msg_count': len(gift_messages)},
                    f, protocol=pickle.HIGHEST_PROTOCOL)

    print("Finished with the gifting stuff!")


