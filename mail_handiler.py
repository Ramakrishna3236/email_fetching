import imaplib, email, poplib
from .models import AdminEmails
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from .models import MailFetch
import logging
import os
logger = logging.getLogger(__name__)
from django.conf import settings
downloads = os.path.join(settings.BASE_DIR, 'email_downloads')


def fetch_emails(ids):
    try:
        instance_email = MailFetch.objects.get(company__id=ids)
        email_user = instance_email.email_user
        email_pass = instance_email.email_pass
        start_ids = instance_email.updated_id
        email_host = instance_email.email_host
        port = instance_email.email_port
        email_server_name = instance_email.email_server_name
        # code for imap server
        if email_server_name == 'imap':
            con = imaplib.IMAP4_SSL(email_host, port)  # connecting to imap server
            con.login(email_user, email_pass)  # authentication done here
            con.list()
            con.select()
            type, data = con.search(None, "ALL") # to return ids
            mail_ids = data[0]
            id_list = mail_ids.split()
            instance_email.updated_id = id_list[-1].decode('utf-8')
            instance_email.save()
            if start_ids == id_list[-1].decode('utf-8'):
                logger.info('no new emails fund ')
            else:
                for num in id_list[start_ids::]:
                    types, data = con.fetch(num, '(RFC822)')
                    raw_email = data[0][1]
                    # converts byte to string
                    raw_email_string = raw_email.decode('utf-8')
                    email_msg = email.message_from_string(raw_email_string)
                    for part in email_msg.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue
                        fileName = part.get_filename()
                        if bool(fileName):
                            filePath = os.path.join(downloads,  fileName)
                            if not os.path.isfile(filePath):
                                with open(filePath, 'wb') as fp:
                                    fp.write(part.get_payload(decode=True))
                                # fp.close()
                                # subject = str(email_msg).split('Subject:', 1)[1].split('\nTo:', 1)[0]
                                # print('Downlaoded "{file}" from email titled "{subject} with {uid}"  '.format(file=fileName,subject=subject,uid=num.decode('utf-8')))

        elif email_server_name == 'pop':
            pop3server = poplib.POP3_SSL(email_host,port)  # open connection
            pop3server.user(email_user)
            pop3server.pass_(email_pass)
            pop3info = pop3server.stat()  # access mailbox status
            resp, mails, octets = pop3server.list()
            last_index = int(mails[-1].decode('utf-8').split()[0])
            instance_email.updated_id=last_index
            instance_email.save()
            if start_ids == last_index:
                logger.info('no new emails')
            else:
                for num in range(start_ids, last_index):
                    response = pop3server.retr(num + 1 )
                    raw_message = response[1]
                    str_message = email.message_from_bytes(b'\n'.join(raw_message))
                    # save attaches
                    for part in str_message.walk():
                        # print(part.get_content_type())
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            # print("no content dispo")
                            continue
                        fileName = part.get_filename()
                        if bool(fileName):
                            filePath = os.path.join(downloads, fileName)
                            print(filePath)
                            if not os.path.isfile(filePath):
                                with open(filePath, 'wb') as fp:
                                # fp = open(filePath, 'wb')
                                    fp.write(part.get_payload(decode=1))
                                # fp.close

        print('completed')
    except Exception as e:
        logger.info(e)
        logger.info('No data is there in our database')
    return


# function for sending emails to applicants
def send_mail_to_applicants(data, company_obj,mail_obj=None,):
    if not mail_obj:
        try:
            mail_obj = AdminEmails.objects.filter(default_email=True, company__id=company_obj)[0]
        except Exception as e:
            logger.info(e)
        try:
            if not mail_obj:
                mail_obj = AdminEmails.objects.all()[0]
        except Exception as e:
            logger.info(e)
            return
    backend = EmailBackend(host=mail_obj.host_address, port=mail_obj.port_no, username=mail_obj.email,
                           password=mail_obj.password, use_tls=mail_obj.use_tls, fail_silently=False)
    # with custom details (to_email, subject, message/body)
    for j in [i for i in data]:
        to =[]
        to.append(j['to'])  # receiver email
        message = j['msg']  # email body
        mail_subject = j['subject']  # email subject
        email = EmailMultiAlternatives(mail_subject, message,from_email=mail_obj.email,to=to, connection=backend )
        email.attach_alternative(message, 'text/html')
        email.send()
    return
