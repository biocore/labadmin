import errno
import smtplib
import socket

from email.mime.text import MIMEText

from knimin.lib.configuration import config


def send_email(message, subject, recipient='americangut@gmail.com',
               sender=config.help_email, bcc=None, html=False, debug=False):
    """Send an email from your local host

    Parameters
    ----------
    message : str
        Body of the email
    subject : str
        Subject of the email
    recipient : str, optional
        Who to send the email to. Default americangut@gmail.com
    sender : str, optional
        Who the email is sent from. Default setting in config.help_email
    bcc : list of str, optional
        If given, email addresses to BCC on the email. Default None
    html : Bool, optional
        Whether the message is HTML format. Default False
    debug : bool, optional
        Whether to return the MIMEText object or sen the email. Useful for
        testing. Default False (Send the email)

    Returns
    -------
    MIMEText object
        If debug is true, the MIMEText object making up the email.
    """

    msg = MIMEText(message, "html" if html else "plain")

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg_bcc = bcc if bcc is not None else []

    # If debugging, just return the built email
    if debug:
        return {'mimetext': msg, 'recipients': [recipient] + msg_bcc}

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    if config.smtp_ssl:
        s = smtplib.SMTP_SSL()
    else:
        s = smtplib.SMTP()

    try:
        s.connect(config.smtp_host, config.smtp_port)
    except socket.error as e:
        # TODO: Inability to connect to the mail server shouldn't prevent pages
        # from loading but it should be logged in some way
        if e.errno == errno.ECONNREFUSED:
            return
        else:
            raise

    # try tls, if not available on server just ignore error
    try:
        s.starttls()
    except smtplib.SMTPException:
        pass

    s.ehlo_or_helo_if_needed()

    if config.smtp_user:
        s.login(config.smtp_user, config.smtp_password)

    # Send with BCC from http://stackoverflow.com/a/1546435
    s.sendmail(sender, [recipient] + msg_bcc, msg.as_string())
    s.quit()
