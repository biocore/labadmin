from tornado.web import authenticated
from future.utils import viewitems

from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.lib.mem_zip import InMemoryZip
from knimin.handlers.access_decorators import set_access


@set_access(['Metadata Pulldown'])
class AGPulldownHandler(BaseHandler):
    @authenticated
    def get(self):
        surveys = db.list_external_surveys()
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=[], surveys=surveys, errors='')

    @authenticated
    def post(self):
        # Do nothing if no file given
        if 'barcodes' not in self.request.files:
            surveys = db.list_external_surveys()
            self.render("ag_pulldown.html", currentuser=self.current_user,
                        barcodes='', blanks='', external='', surveys=surveys,
                        errors="No barcode file given, thus nothing could "
                               "be pulled down.")
            return
        # Get file information, ignoring commented out lines
        fileinfo = self.request.files['barcodes'][0]['body']
        lines = fileinfo.splitlines()
        # barcodes must be in first column, stripping in case extra spaces
        samples = [l.split('\t')[0].strip() for l in lines
                   if not l.startswith('#')]
        barcodes = [b for b in samples if not b.upper().startswith('BLANK')]
        blanks = [b for b in samples if b.upper().startswith('BLANK')]
        hold = self.get_arguments('external', [])
        if hold:
            external = ','.join(hold)
        else:
            external = ''
        surveys = db.list_external_surveys()
        self.render("ag_pulldown.html", currentuser=self.current_user,
                    barcodes=",".join(barcodes), blanks=",".join(blanks),
                    surveys=surveys, external=external, errors='')


@set_access(['Metadata Pulldown'])
class AGPulldownDLHandler(BaseHandler):
    @authenticated
    def post(self):
        barcodes = self.get_argument('barcodes').split(',')
        if self.get_argument('blanks'):
            blanks = self.get_argument('blanks').split(',')
        else:
            blanks = []
        if self.get_argument('external'):
            external = self.get_argument('external').split(',')
        else:
            external = []
        # Get metadata and create zip file
        metadata, failures = db.pulldown(barcodes, blanks, external)

        meta_zip = InMemoryZip()
        failed = '\n'.join(['\t'.join(bc) for bc in viewitems(failures)])
        failtext = ("The following barcodes were not retrieved "
                    "for any survey:\n%s" % failed)
        meta_zip.append("failures.txt", failtext)
        for survey, meta in viewitems(metadata):
            meta_zip.append('survey_%s_md.txt' % survey, meta)

        # write out zip file
        self.add_header('Content-type',  'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=metadata.zip')
        self.write(meta_zip.write_to_buffer())
        self.flush()
        self.finish()


@set_access(['Metadata Pulldown'])
class UpdateEBIStatusHandler(BaseHandler):
    @authenticated
    def get(self):
        try:
            db.set_deposited_ebi()
            msg = 'Successfully updated barcodes in database'
        except Exception as e:
            msg = 'ERROR: %s' % str(e)
        self.write(msg)
