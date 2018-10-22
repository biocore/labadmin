from tornado.web import authenticated

from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db
from knimin.lib.mem_zip import InMemoryZip


@set_access(['Admin'])
class AGNamesHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_participant_names.html", currentuser=self.current_user)

    @authenticated
    def post(self):
        self.render("ag_participant_names.html", currentuser=self.current_user)


class AGNamesDLHandler(BaseHandler):
    @authenticated
    def post(self):
        participants = db.participant_names()
        participants = '\n'.join(['\t'.join(r) for r in participants])

        meta_zip = InMemoryZip()
        meta_zip.append('participants.txt', participants)

        # write out zip file
        self.add_header('Content-type', 'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=participants.zip')
        self.write(meta_zip.write_to_buffer())
        self.flush()
        self.finish()
