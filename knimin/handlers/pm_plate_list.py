from tornado.web import authenticated
from knimin.handlers.base import BaseHandler
from knimin import db
from knimin.handlers.access_decorators import set_access


@set_access(['Admin'])
class PMPlateListHandler(BaseHandler):
    @authenticated
    def get(self):
        target = self.get_argument("target", default="sample")
        plates = db.get_sample_plate_list()
        self.render("pm_plate_list.html", currentuser=self.current_user,
                    target=target, plates=plates)
