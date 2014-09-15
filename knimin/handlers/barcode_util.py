#!/usr/bin/env pythonget_barcode_info_by_kit_id
from knimin.handlers.base import BaseHandler
from urllib import unquote


from amgut.util import AG_DATA_ACCESS


class BarcodeUtilHandler(BaseHandler):
    def get(self):
        self.render("barcode_util.html", div_and_msg=None, proj=None,
                    project_names=None, barcode=None, email_type=None,
                    barcode_info=None, proj_barcode_info=None,
                    loginerror='')

    def post(self):
        barcode = self.get_argument('barcode', None)
        bstatus = self.get_argument('bstatus', None)
        postmark_date = self.get_argument('postmark_date', None)
        scan_date = self.get_argument('scan_date', None)
        biomass_remaining_value = self.get_argument('biomass_remaining_value',
                                                    None)
        sequncing_status = self.get_argument('sequencing_status', None)
        obsolete_status = self.get_argument('obsolete_status', None)
        project = self.get_argument('project', None)
        proj_type = 'Unknown'
        ag_details = {}
        if bstatus is None:
            # gather info to display
            barcode_details = AG_DATA_ACCESS.get_barcode_details(barcode)
            if len(barcode_details) == 0:
                div_id = "invalid_barcode"
                message = ("Barcode %s does not exisit in the database" %
                           barcode)
            else:
                proj_type = AG_DATA_ACCESS.getBarcodeProjType(barcode)
                # proj_group = AG_DATA_ACCESS.getProjectGroup(proj_type)
                proj_group = "American Gut"
                project_names = AG_DATA_ACCESS.getProjectNames()
                # barcode exists get general info
                if barcode_details['status'] is None:
                    barcode_details['status'] = 'Received'
                if barcode_details['scan_date'] is None:
                    barcode_details['scan_date'] = 'NA'
                if barcode_details['sample_postmark_date'] is None:
                    barcode_details['sample_postmark_date'] = 'NA'
                if barcode_details['biomass_remaining'] is None:
                    barcode_details['biomass_remaining'] = 'Unknown'
                if barcode_details['sequencing_status'] is None:
                    barcode_details['sequencing_status']
                if barcode_details['obsolete'] is None:
                    barcode_details['obsolete'] = 'N'
                div_id = message = email_type = ""
                ag_details = []
                if (barcode_details['obsolete'] == "Y"):
                        #the barcode is obsolete
                        div_id = "obsolete"
                        message = "Barcode is Obsolete"
                #get project info for div
                elif proj_group == 'American Gut':
                    div_id, message, ag_details = self.get_ag_details(barcode)
                else:
                    div_id = "verified"
                    message = "Barcode Info is correct"
        div_and_msg = (div_id, message, barcode)
        self.render("barcode_util.html", div_and_msg=div_and_msg,
                    proj=proj_group, project_names=project_names,
                    barcode=barcode, email_type=None,
                    barcode_info=barcode_details, proj_barcode_info=ag_details,
                    loginerror='')
        return

    def get_ag_details(self, barcode):
        ag_details = AG_DATA_ACCESS.getAGBarcodeDetails(barcode)
        if len(ag_details) > 0:
            if ag_details['site_sampled'] is None:
                ag_details['site_sampled'] = ''
            if ag_details['sample_date'] is None:
                ag_details['sample_date'] = ''
            if ag_details['sample_time'] is None:
                ag_details['sample_time'] = ''
            if ag_details['moldy'] is None:
                ag_details['moldy'] = 'NA'
            if ag_details['overloaded'] is None:
                ag_details['overloaded'] = 'NA'
            if ag_details['other'] is None:
                ag_details['other'] = 'NA'
            if ag_details['other_text'] is None:
                ag_details['other_text'] = ''
            if ag_details['date_of_last_email'] is None:
                ag_details['date_of_last_email'] = ''
            if ag_details['email'] is None:
                ag_details['email'] = ''
            if ag_details['name'] is None:
                ag_details['login_user'] = ''
            else:
                ag_details['login_user'] = \
                    ag_details['name']
            if ag_details['moldy'] == 'Y':
                ag_details['moldy_checked'] = 'checked'
            else:
                ag_details['moldy_checked'] = ''
            if ag_details['overloaded'] == 'Y':
                ag_details['overloaded_checked'] = 'checked'
            else:
                ag_details['overloaded_checked'] = ''
            if ag_details['other'] == 'Y':
                ag_details['other_checked'] = 'checked'
            else:
                ag_details['other_checked'] = ''

            barcode_metadata = AG_DATA_ACCESS.AGGetBarcodeMetadata(
                barcode)
            if not (ag_details['sample_date'] ==
                    ag_details['site_sampled'] ==
                    ag_details['sample_time'] == ''):
                # it has all sample details
                # (sample time, date, site)
                if len(barcode_metadata) == 1:
                    # and we can successfully retrieve sample
                    # metadata
                    div_id = "verified"
                    message = "All good"
                    ag_details['email_type'] = "1"
                elif len(barcode_metadata) == 0:
                    barcode_metadata_animal = \
                        AG_DATA_ACCESS.AGGetBarcodeMetadataAnimal(
                            barcode)
                    if len(barcode_metadata_animal) == 0:
                        div_id = "no_metadata"
                        message = "Cannot retrieve metadata"
                    elif len(barcode_metadata_animal) == 1:
                        div_id = "verified_animal"
                        message = "All good"
                        ag_details['email_type'] = "1"
                else:
                    # should never get here (this would happen
                    # if the metadata
                    # pulldown returned more than one row for a
                    # single barcode)
                    div_id = "md_pulldown_error"
                    message = ("This barcode has multiple entries "
                               "in the database, which should "
                               "never happeen. Please notify "
                               "someone on the database crew.")
            else:
                div_id = "not_assigned"
                message = "Missing info"
                ag_details['email_type'] = "0"
        else:
            div_id = "not_assigned"
            message = ("In American Gut project group but No "
                       "Amerincan Gut info for barcode")
        return div_id, message, ag_details
