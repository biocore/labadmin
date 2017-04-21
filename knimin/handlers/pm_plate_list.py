from tornado.web import authenticated

from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        self.render("pm_plate_list.html", currentuser=self.current_user)


@set_access(['Admin'])
class PMSamplePlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = db.get_sample_plate_list()
        headers = ['id', 'name', 'type', 'filled', 'studies', 'person',
                   'date']
        for p in plates:
            p['date'] = p['date'].isoformat()
            p['type'] = p['type'][0]
            p['filled'] = "%d (%.1f %%)" % (p['fill'][0], p['fill'][1] * 100)
            p['studies'] = '</br>'.join(p['studies'])
        self.write({'headers': headers, 'plates': plates})
        self.finish()


@set_access(['Admin'])
class PMDNAPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = db.get_dna_plate_list()
        for p in plates:
            p['date'] = p['date'].isoformat()
        headers = ['id', 'name', 'date']
        self.write({'headers': headers, 'plates': plates})
        self.finish()


@set_access(['Admin'])
class PMTargetedPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = db.get_targeted_plate_list()
        for p in plates:
            p['date'] = p['date'].isoformat()
        headers = ['id', 'name', 'date', 'num_samples']
        self.write({'headers': headers, 'plates': plates})
        self.finish()


@set_access(['Admin'])
class PMShotgunPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = db.get_shotgun_plate_list()
        for p in plates:
            p['date'] = p['date'].isoformat()
            p['dna_plates'] = "</br>".join(p['dna_plates'])

        headers = ['id', 'name', 'date', 'dna_plates']
        self.write({'headers': headers, 'plates': plates})
        self.finish()


@set_access(['Admin'])
class PMShotgunNormalizedPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        plates = db.get_normalized_shotgun_plate_list()
        for p in plates:
            p['date'] = p['date'].isoformat()

        headers = ['id', 'name', 'date']
        self.write({'headers': headers, 'plates': plates})
        self.finish()
