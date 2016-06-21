from unittest import TestCase, main

from knimin.lib.mail import send_email


class TestEmail(TestCase):
    def test_send_email_basic(self):
        obs = send_email('test message', 'test subject', debug=True)
        self.assertEqual(obs['mimetext']['To'],
                         'americangut@gmail.com')
        self.assertEqual(obs['mimetext']['From'], '')
        self.assertEqual(obs['mimetext']['Subject'],
                         'test subject')
        self.assertEqual(obs['recipients'],
                         ['americangut@gmail.com'])

    def test_send_email_full(self):
        obs = send_email('test message', 'test subject',
                         recipient='recipient@somewhere.com',
                         sender='sender@place.com', bcc=['bcc@mail.com'],
                         debug=True)
        self.assertEqual(obs['mimetext']['To'],
                         'recipient@somewhere.com')
        self.assertEqual(obs['mimetext']['From'], 'sender@place.com')
        self.assertEqual(obs['mimetext']['Subject'],
                         'test subject')
        self.assertEqual(obs['recipients'],
                         ['recipient@somewhere.com', 'bcc@mail.com'])


if __name__ == '__main__':
    main()
