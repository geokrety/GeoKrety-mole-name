import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        # Send the message via local SMTP server.
        s = smtplib.SMTP(self.config.get('EMAIL_SMTP_HOST', "smtp.gmail.com"), self.config.get('EMAIL_SMTP_PORT', '587'))

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
        subject = "GeoKrety - Confirm your vote"
        text = "Hi!\nThanks you for participating in finding our mascot a name.\nPlease clic (or copy/paste) this link %s/validate/%s to validate your vote."
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               Thanks you for participating in finding our mascot a name.<br>
               You have voted for <q>%s</q><br>
               Please clic this <a href="%s/validate/%s">link</a> to validate your vote.
            </p>
          </body>
        </html>
        """ % (
            name,
            self.config.get('SITE_BASE', "https://molename.geokrety.org"),
            token
        )
        self._send(to, subject, text, html)
