from collections import defaultdict, OrderedDict
from datetime import datetime
from threading import Thread

from flask import current_app, render_template, url_for
from flask_mail import Message
from oauth2client.service_account import ServiceAccountCredentials

from app import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, recipients, text_body, html_body,
               attachments=None, sender=None,
               sync=False):
    if sender is None:
        sender = current_app.config['MAIL_SENDER']
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(target=send_async_email,
               args=(current_app._get_current_object(), msg)).start()
