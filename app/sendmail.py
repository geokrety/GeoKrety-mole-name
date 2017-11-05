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
    def send(self, to, token, name):
        subject = render_template('send-confirmation-subject.html')
        url = self.config.get('SITE_BASE', "https://molename.geokrety.org") + url_for('validate', token=token)
        text = render_template('send-confirmation-text.html', name=name, url=url)
        html = render_template('send-confirmation.html', name=name, url=url)
        self._send(to, subject, text, html)


class sendProposition(send):
    def send(self, name):
        subject = "GeoKrety - New mole name proposition"
        text = """Hi!\nSomeone proposed a new mole name: "%s".\nPlease review the proposition at %s/moderate/%s""" % (
            name,
            self.config.get('SITE_BASE', "https://molename.geokrety.org"),
            self.config.get('ADMIN_PASSWORD'),
        )
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               Someone proposed a new mole name: <q>%s</q>.<br>
               Please <a href="%s/moderate/%s">review the proposition</a>.
            </p>
          </body>
        </html>
        """ % (
            name,
            self.config.get('SITE_BASE', "https://molename.geokrety.org"),
            self.config.get('ADMIN_PASSWORD'),
        )
        self._send(self.config.get('EMAIL_FROM', "geokrety@gmail.com"), subject, text, html)
