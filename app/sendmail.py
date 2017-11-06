import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import render_template, url_for
from ihih import IHIH


class send:

    def __init__(self):
        self.config = conf = IHIH(
            (
                os.path.join(os.path.dirname(__file__), '../config/custom.conf')
            )
        )

    def _send(self, to, subject, text, html):
        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config.get('EMAIL_FROM', 'geokrety@gmail.com')
        msg['To'] = to

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain', 'utf-8')
        part2 = MIMEText(html, 'html', 'utf-8')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        # Send the message via local SMTP server.
        s = smtplib.SMTP(self.config.get('EMAIL_SMTP_HOST', "smtp.gmail.com"),
                         self.config.get('EMAIL_SMTP_PORT', '587'))

        if self.config.get_bool('EMAIL_TLS', True):
            s.starttls()

        login = self.config.get('EMAIL_USERNAME')
        password = self.config.get('EMAIL_PASSWORD')
        # if login and password:
        s.login(login, password)

        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        s.sendmail(self.config.get('EMAIL_FROM', 'geokrety@gmail.com'), to, msg.as_string())
        s.quit()


class sendConfirmation(send):
    def send(self, email, token, name):
        subject = render_template('send-confirmation-subject.html')
        url = self.config.get('SITE_BASE', "https://molename.geokrety.org") + url_for('validate', token=token)
        text = render_template('send-confirmation-text.html', name=name, url=url)
        html = render_template('send-confirmation.html', name=name, url=url)
        self._send(email, subject, text, html)


class sendProposition(send):
    def send(self, username, name):
        url = self.config.get('SITE_BASE', "https://molename.geokrety.org") + url_for('moderation_list', password=self.config.get('ADMIN_PASSWORD'))
        subject = "GeoKrety - New mole name proposition"
        text = """Hi!\n'%s' proposed a new mole name: "%s".\nPlease review the proposition at %s""" % (username, name, url)
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               Someone proposed a new mole name: <q>%s</q>.<br>
               Please <a href="%s">review the proposition</a>.
            </p>
          </body>
        </html>
        """ % (name, url)
        self._send(self.config.get('EMAIL_FROM', "geokrety@gmail.com"), subject, text, html)


class sendValidatedProposition(send):
    def send(self, username, email, name):
        url = self.config.get('SITE_BASE', "https://molename.geokrety.org") + url_for('moderation_list', password=self.config.get('ADMIN_PASSWORD'))
        subject = "GeoKrety - Your name proposition has been accepted"
        text = """Congratulation %s!\nYour name proposition (%s) has been accepted by a moderator.\nThanks again for your participation.\n\nThe GK Team""" % (username, name)
        html = """\
        <html>
          <head></head>
          <body>
            <p>Congratulation %s!<br>
               Your name proposition (%s) has been accepted by a moderator.<br>
               Thanks again for your participation.
            </p>
            <p>The GK Team</p>
          </body>
        </html>
        """ % (username, name)
        self._send(email, subject, text, html)
