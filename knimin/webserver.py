from os.path import dirname, join
from base64 import b64encode
from uuid import uuid4

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado.options import define, options, parse_command_line

from knimin.lib.configuration import config
from knimin.handlers.base import MainHandler, NoPageHandler
from knimin.handlers.auth_handlers import AuthLoginHandler, AuthLogoutHandler
from knimin.handlers.ag_search import AGSearchHandler
from knimin.handlers.logged_in_index import LoggedInIndexHandler
from knimin.handlers.barcode_util import BarcodeUtilHandler
from knimin.handlers.ag_stats import AGStatsHandler
from knimin.handlers.ag_edit_participant import AGEditParticipantHandler
from knimin.handlers.ag_new_kit import AGNewKitHandler, AGNewKitDLHandler
from knimin.handlers.ag_new_barcode import (AGNewBarcodeHandler,
                                            AGBarcodePrintoutHandler,
                                            AGBarcodeAssignedHandler)
from knimin.handlers.ag_edit_barcode import AGEditBarcodeHandler
from knimin.handlers.ag_update_geocode import AGUpdateGeocodeHandler
from knimin.handlers.ag_pulldown import (
    AGPulldownHandler, AGPulldownDLHandler, UpdateEBIStatusHandler)
from knimin.handlers.ag_add_barcode_kit import AGAddBarcodeKitHandler
from knimin.handlers.ag_get_participant_names import (AGNamesHandler,
                                                      AGNamesDLHandler)
from knimin.handlers.ag_third_party import (AGThirdPartyHandler,
                                            AGNewThirdPartyHandler)
from knimin.handlers.ag_consent_check import AGConsentCheckHandler
from knimin.handlers.projects_summary import ProjectsSummaryHandler
from knimin.handlers.access_control import AGEditAccessHandler
from knimin.handlers.ag_results_ready import AGResultsReadyHandler
from knimin.handlers.pm_plate_list import PMPlateListHandler
from knimin.handlers.pm_plate_map import (
    PMCreatePlateHandler, PMPlateNameCheckerHandler, PMPlateMapHandler,
    PMSamplePlateHandler, PMExtractPlateHandler)
from knimin.handlers.pm_create_study import (PMCreateStudyHandler,
                                             PMJiraUserCheckerHandler)
from knimin.handlers.pm_library_prep import (
    PMTargetGeneLibraryPrepHandler,
    PMMetagenomicsLibraryPrepHandler, PMMetagenomicsLibraryPrepEchoHandler)
from knimin.handlers.pm_pool_handlers import (
    PMTargetedConcentrationHandler, PMTargetedConcentrationCheckHandler,
    PMTargetedPoolHandler, PMTargetedPoolEPMotionHandler)
from knimin.handlers.pm_sequence import (
    PMSequenceHandler, PMSequencingCompleteHandler)
from knimin.handlers.pm_condense import PMCondensePlatesHandler
from knimin.handlers.pm_shotgun_pool import PMShotgunPool
from knimin.handlers.pm_normalize import (
    PMNormalizeHandler, PMNormalizeEchoFileHandler)

define("port", default=config.http_port, type=int)

DIRNAME = dirname(__file__)
STATIC_PATH = join(DIRNAME, "static")
TEMPLATE_PATH = join(DIRNAME, "templates")  # base folder for webpages
COOKIE_SECRET = b64encode(uuid4().bytes + uuid4().bytes)


class WebApplication(Application):
    def __init__(self):
        handlers = [
            (r"/results/(.*)", StaticFileHandler,
                {"path": '/tmp/'}),
            (r"/static/(.*)", StaticFileHandler, {"path": STATIC_PATH}),
            (r"/", MainHandler),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/logged_in_index/", LoggedInIndexHandler),
            (r"/ag_search/", AGSearchHandler),
            (r"/barcode_util/", BarcodeUtilHandler),
            (r"/ag_add_barcode_kit/", AGAddBarcodeKitHandler),
            (r"/ag_stats/", AGStatsHandler),
            (r"/ag_edit_participant/", AGEditParticipantHandler),
            (r"/ag_new_kit/", AGNewKitHandler),
            (r"/ag_new_kit/download/", AGNewKitDLHandler),
            (r"/ag_new_barcode/", AGNewBarcodeHandler),
            (r"/ag_update_geocode/", AGUpdateGeocodeHandler),
            (r"/update_ebi/", UpdateEBIStatusHandler),
            (r"/update_ready/", AGResultsReadyHandler),
            (r"/ag_edit_barcode/", AGEditBarcodeHandler),
            (r"/ag_pulldown/", AGPulldownHandler),
            (r"/ag_pulldown/download/", AGPulldownDLHandler),
            (r"/ag_participant_names/", AGNamesHandler),
            (r"/ag_participant_names/download/", AGNamesDLHandler),
            (r"/ag_new_barcode/download/", AGBarcodePrintoutHandler),
            (r"/ag_new_barcode/assigned/", AGBarcodeAssignedHandler),
            (r"/ag_third_party/data/", AGThirdPartyHandler),
            (r"/ag_third_party/add/", AGNewThirdPartyHandler),
            (r"/projects/summary/", ProjectsSummaryHandler),
            (r"/admin/edit/", AGEditAccessHandler),
            (r"/consent_check", AGConsentCheckHandler),
            # PlateMapper Handlers
            (r"/pm_library_prep/target_gene/", PMTargetGeneLibraryPrepHandler),
            (r"/pm_library_prep/metagenomics/echo/",
             PMMetagenomicsLibraryPrepEchoHandler),
            (r"/pm_library_prep/metagenomics/",
             PMMetagenomicsLibraryPrepHandler),
            (r"/pm_targeted_concentration/", PMTargetedConcentrationHandler),
            (r"/pm_targeted_concentration_check/",
             PMTargetedConcentrationCheckHandler),
            (r"/pm_targeted_pool/", PMTargetedPoolHandler),
            (r"/pm_targeted_pool_epmotion/", PMTargetedPoolEPMotionHandler),
            (r"/pm_sequence/", PMSequenceHandler),
            (r"/pm_sequencing_complete/", PMSequencingCompleteHandler),
            (r"/pm_create_study/", PMCreateStudyHandler),
            (r"/pm_plate_list/", PMPlateListHandler),
            (r"/pm_jira_user_check/", PMJiraUserCheckerHandler),
            (r"/pm_create_plate/", PMCreatePlateHandler),
            (r"/pm_sample_plate/name_check", PMPlateNameCheckerHandler),
            (r"/pm_sample_plate", PMSamplePlateHandler),
            (r"/pm_plate_map", PMPlateMapHandler),
            (r"/pm_extract_plate", PMExtractPlateHandler),
            (r"/pm_condense/", PMCondensePlatesHandler),
            (r"/pm_shotgun_pool/", PMShotgunPool),
            (r"/pm_normalize/", PMNormalizeHandler),
            (r"/pm_normalize_echo/", PMNormalizeEchoFileHandler),
            (r".*", NoPageHandler)
        ]
        settings = {
            "template_path": TEMPLATE_PATH,
            "debug": config.debug,
            "cookie_secret": COOKIE_SECRET,
            "login_url": "/login/",
        }
        super(WebApplication, self).__init__(handlers, **settings)


def main():
    # format looks like labadmin_8888.log
    prefix = join(config.base_log_dir, "labadmin_%d.log" % options.port)
    options.log_file_prefix = prefix
    parse_command_line()
    http_server = HTTPServer(WebApplication())
    http_server.listen(options.port)
    print("Tornado started on port %d" % options.port)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()
