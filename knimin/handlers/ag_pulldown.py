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
        barcodes = self.get_argument('barcodes').split("\n")
        if len(barcodes) == 1:
            # Windows newlines
            barcodes = self.get_argument('barcodes').split("\r")
        barcodes = map(lambda x: x.strip(), barcodes)
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=barcodes)


class AGPulldownDLHandler(BaseHandler):
    def get(self):
        barcodes = self.get_argument('barcodes').split(",")
        # Get metadata and create zip file
        metadata, failures = db.pulldown(barcodes)
        meta_zip = InMemoryZip()
        failtext = ("The following barcodes were not retrieved for any "
                    "survey:\n%s" % "\n".join(failures))
        meta_zip.append("failures.txt", failtext)
        for survey, meta in viewitems(metadata):
            meta_zip.append('survey_%d_md.txt' % survey, meta)

        # write out zip file
        self.add_header('Content-type',  'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition', 'attachment; filename=metadata.zip')
        self.write(meta_zip.in_memory_zip)
        self.flush()
        self.finish()
