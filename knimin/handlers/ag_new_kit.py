from json import loads
from tornado.web import authenticated, HTTPError
from tornado.escape import url_unescape
from knimin.handlers.base import BaseHandler
from knimin.handlers.access_decorators import set_access
from knimin import db
from knimin.lib.mem_zip import InMemoryZip
from knimin.lib.util import get_printout_data


@set_access(['AG kits'])
class AGNewKitDLHandler(BaseHandler):
    @authenticated
    def post(self):
        kitinfo = loads(self.get_argument('kitinfo'))
        fields = self.get_argument('fields').split(',')
        table = ['\t'.join(fields)]
        table.extend(['\t'.join(map(str, kit)) for kit in kitinfo])
        kit_zip = InMemoryZip()
        kit_zip.append('kit_printouts.txt', get_printout_data(kitinfo)).append(
            'kit_table.txt', '\n'.join(table))
        # write out zip file
        self.add_header('Content-type', 'application/octet-stream')
        self.add_header('Content-Transfer-Encoding', 'binary')
        self.add_header('Accept-Ranges', 'bytes')
        self.add_header('Content-Encoding', 'none')
        self.add_header('Content-Disposition',
                        'attachment; filename=kitinfo.zip')
        self.write(kit_zip.write_to_buffer())
        self.flush()
        self.finish()


@set_access(['AG kits'])
class AGNewKitHandler(BaseHandler):
    @authenticated
    def get(self):
        project_names = db.getProjectNames()
        remaining = len(db.get_unassigned_barcodes())

        self.render("ag_new_kit.html", projects=project_names,
                    currentuser=self.current_user, msg="", kitinfo=[],
                    fields="", remaining=remaining)

    @authenticated
    def post(self):
        tag = self.get_argument("tag")
        if not tag:
            tag = None
        projects = [url_unescape(p).encode('utf-8')
                    for p in self.get_arguments("projects")]
        num_swabs = map(int, self.get_arguments("swabs"))
        num_kits = map(int, self.get_arguments("kits"))
        kits = []
        fields = ""
        try:
            kits = db.create_ag_kits(zip(num_swabs, num_kits), tag, projects)
            fields = ','.join(kits[0]._fields)
        except Exception as e:
            raise HTTPError(500, "ERROR: %s" % e.message.encode('utf-8'))

        self.write({'kitinfo': kits, 'fields': fields})
