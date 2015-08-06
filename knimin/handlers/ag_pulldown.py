from tornado.web import authenticated
from future.utils import viewitems

from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.lib.mem_zip import InMemoryZip


class AGPulldownHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=[])

    def post(self):
        # Get file information, ignoring commented out lines
        fileinfo = self.request.files['filearg'][0]['body']
        lines = fileinfo.splitlines()
        # barcodes must be in first column, stripping in case extra spaces
        barcodes = [l.split('\t')[0].strip() for l in lines
                    if not l.startswith('#')]
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=",".join(barcodes))


class AGPulldownDLHandler(BaseHandler):
    def post(self):
        barcodes = self.get_argument('barcodes').split(',')
        # Get metadata and create zip file
        metadata, failures = db.pulldown(barcodes)

        meta_zip = InMemoryZip()
        failtext = ("The following barcodes were not retrieved for any "
                    "survey:\n%s" % "\n".join(failures))
        meta_zip.append("failures.txt", failtext)
        for survey, meta in viewitems(metadata):
            meta_zip.append('survey_%s_md.txt' % survey, meta)

        # write out zip file
        self.add_header('Content-type',  'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition', 'attachment; filename=metadata.zip')
        self.write(meta_zip.write_to_buffer())
        self.flush()
        self.finish()
