#!/usr/bin/env python
from tornado.web import authenticated
from tornado.escape import json_encode
from tornado import gen, concurrent
from knimin.handlers.base import BaseHandler
from datetime import datetime
import StringIO
import requests
import functools
import pandas as pd
from qiita_client import QiitaClient

from knimin import db
from knimin.lib.constants import survey_type
from knimin.lib.mail import send_email
from knimin.handlers.access_decorators import set_access
from knimin.lib.configuration import config


# metadata categories as observed on 15aug2019 from qiita for study 10317
# this variable is for use in testing when mocking out interaction with
# qiita
AG_DEBUG_OBSERVED_CATEGORIES = [
    u'acid_reflux', u'acne_medication', u'acne_medication_otc', u'add_adhd',
    u'age_cat', u'age_corrected', u'age_years', u'alcohol_consumption',
    u'alcohol_frequency', u'alcohol_types', u'alcohol_types_beercider',
    u'alcohol_types_red_wine', u'alcohol_types_sour_beers',
    u'alcohol_types_spiritshard_alcohol', u'alcohol_types_unspecified',
    u'alcohol_types_white_wine', u'allergic_to',
    u'allergic_to_i_have_no_food_allergies_that_i_know_of',
    u'allergic_to_other', u'allergic_to_peanuts', u'allergic_to_shellfish',
    u'allergic_to_tree_nuts', u'allergic_to_unspecified', u'altitude',
    u'alzheimers', u'animal_age', u'animal_free_text', u'animal_gender',
    u'animal_origin', u'animal_type', u'anonymized_name',
    u'antibiotic_history', u'appendix_removed', u'artificial_sweeteners',
    u'asd', u'assigned_from_geo', u'autoimmune',
    u'birth_year', u'bmi', u'bmi_cat', u'bmi_corrected', u'body_habitat',
    u'body_product', u'body_site', u'bowel_movement_frequency',
    u'bowel_movement_quality', u'breastmilk_formula_ensure', u'cancer',
    u'cancer_treatment', u'cardiovascular_disease', u'cat', u'cdiff',
    u'census_region', u'chickenpox', u'clinical_condition', u'collection_date',
    u'collection_date_only', u'collection_month', u'collection_season',
    u'collection_time', u'collection_timestamp',
    u'consume_animal_products_abx',
    u'contraceptive', u'coprophage', u'cosmetics_frequency', u'country',
    u'country_of_birth', u'country_residence', u'csection', u'deodorant_use',
    u'depression_bipolar_schizophrenia', u'depth', u'description', u'diabetes',
    u'diabetes_type', u'diet', u'diet_type', u'dna_extracted', u'dog',
    u'dominant_hand', u'drinking_water_source', u'drinks_per_session',
    u'economic_region', u'elevation', u'env_biome', u'env_feature',
    u'env_material', u'env_package', u'epilepsy_or_seizure_disorder',
    u'exercise_frequency', u'exercise_location', u'fed_as_infant',
    u'fermented_consumed', u'fermented_consumed_beer',
    u'fermented_consumed_chicha', u'fermented_consumed_cider',
    u'fermented_consumed_cottage_cheese',
    u'fermented_consumed_fermented_beansmisonatto',
    u'fermented_consumed_fermented_breadsourdoughinjera',
    u'fermented_consumed_fermented_fish', u'fermented_consumed_fermented_tofu',
    u'fermented_consumed_fish_sauce', u'fermented_consumed_kefir_milk',
    u'fermented_consumed_kefir_water', u'fermented_consumed_kimchi',
    u'fermented_consumed_kombucha', u'fermented_consumed_mead',
    u'fermented_consumed_other', u'fermented_consumed_pickled_vegetables',
    u'fermented_consumed_sauerkraut',
    u'fermented_consumed_sour_creamcreme_fraiche',
    u'fermented_consumed_tempeh',
    u'fermented_consumed_unspecified', u'fermented_consumed_wine',
    u'fermented_consumed_yogurtlassi', u'fermented_frequency',
    u'fermented_increased', u'fermented_other', u'fermented_plant_frequency',
    u'fermented_produce_commercial', u'fermented_produce_commercial_beer',
    u'fermented_produce_commercial_chicha',
    u'fermented_produce_commercial_cider',
    u'fermented_produce_commercial_cottage_cheese',
    u'fermented_produce_commercial_fermented_beansmisonatto',
    u'fermented_produce_commercial_fermented_breadsourdoughinjera',
    u'fermented_produce_commercial_fermented_fish',
    u'fermented_produce_commercial_fermented_tofu',
    u'fermented_produce_commercial_fish_sauce',
    u'fermented_produce_commercial_kefir_milk',
    u'fermented_produce_commercial_kefir_water',
    u'fermented_produce_commercial_kimchi',
    u'fermented_produce_commercial_kombucha',
    u'fermented_produce_commercial_mead',
    u'fermented_produce_commercial_other',
    u'fermented_produce_commercial_pickled_vegetables',
    u'fermented_produce_commercial_sauerkraut',
    u'fermented_produce_commercial_sour_creamcreme_fraiche',
    u'fermented_produce_commercial_tempeh',
    u'fermented_produce_commercial_unspecified',
    u'fermented_produce_commercial_wine',
    u'fermented_produce_commercial_yogurtlassi', u'fermented_produce_personal',
    u'fermented_produce_personal_beer', u'fermented_produce_personal_chicha',
    u'fermented_produce_personal_cider',
    u'fermented_produce_personal_cottage_cheese',
    u'fermented_produce_personal_fermented_beansmisonatto',
    u'fermented_produce_personal_fermented_breadsourdoughinjera',
    u'fermented_produce_personal_fermented_fish',
    u'fermented_produce_personal_fermented_tofu',
    u'fermented_produce_personal_fish_sauce',
    u'fermented_produce_personal_kefir_milk',
    u'fermented_produce_personal_kefir_water',
    u'fermented_produce_personal_kimchi',
    u'fermented_produce_personal_kombucha',
    u'fermented_produce_personal_mead', u'fermented_produce_personal_other',
    u'fermented_produce_personal_pickled_vegetables',
    u'fermented_produce_personal_sauerkraut',
    u'fermented_produce_personal_sour_creamcreme_fraiche',
    u'fermented_produce_personal_tempeh',
    u'fermented_produce_personal_unspecified',
    u'fermented_produce_personal_wine',
    u'fermented_produce_personal_yogurtlassi', u'flossing_frequency',
    u'flu_vaccine_date', u'food_source', u'food_source_human_food',
    u'food_source_pet_store_food', u'food_source_unspecified',
    u'food_source_wild_food', u'food_special', u'food_special_grain_free',
    u'food_special_organic', u'food_special_unspecified', u'food_type',
    u'frozen_dessert_frequency', u'fruit_frequency', u'fungal_overgrowth',
    u'geo_loc_name', u'gluten', u'has_physical_specimen', u'height_cm',
    u'height_units', u'high_fat_red_meat_frequency',
    u'homecooked_meals_frequency',
    u'host', u'host_common_name', u'host_subject_id', u'host_taxid',
    u'hours_outside', u'humans_free_text', u'ibd', u'ibd_diagnosis',
    u'ibd_diagnosis_refined', u'ibs', u'kidney_disease', u'lactose',
    u'last_move',
    u'last_travel', u'latitude', u'level_of_education', u'liver_disease',
    u'living_status', u'livingwith', u'longitude', u'lowgrain_diet_type',
    u'lung_disease', u'meat_eggs_frequency', u'mental_illness',
    u'mental_illness_type', u'mental_illness_type_anorexia_nervosa',
    u'mental_illness_type_bipolar_disorder',
    u'mental_illness_type_bulimia_nervosa', u'mental_illness_type_depression',
    u'mental_illness_type_ptsd_posttraumatic_stress_disorder',
    u'mental_illness_type_schizophrenia',
    u'mental_illness_type_substance_abuse',
    u'mental_illness_type_unspecified', u'migraine', u'milk_cheese_frequency',
    u'milk_substitute_frequency', u'multivitamin', u'nail_biter', u'name',
    u'non_food_allergies', u'non_food_allergies_beestings',
    u'non_food_allergies_drug_eg_penicillin', u'non_food_allergies_pet_dander',
    u'non_food_allergies_poison_ivyoak', u'non_food_allergies_sun',
    u'non_food_allergies_unspecified', u'olive_oil',
    u'one_liter_of_water_a_day_frequency', u'other_animals_free_text',
    u'other_supplement_frequency', u'pets_other', u'pets_other_freetext',
    u'physical_specimen_location', u'physical_specimen_remaining', u'pku',
    u'pool_frequency', u'poultry_frequency', u'pregnant',
    u'prepared_meals_frequency', u'probiotic_frequency', u'public',
    u'qiita_empo_1', u'qiita_empo_2', u'qiita_empo_3', u'race',
    u'ready_to_eat_meals_frequency', u'red_meat_frequency', u'roommates',
    u'roommates_in_study', u'salted_snacks_frequency', u'sample_type',
    u'scientific_name', u'seafood_frequency', u'seasonal_allergies',
    u'setting',
    u'sex', u'sibo', u'skin_condition', u'sleep_duration',
    u'smoking_frequency',
    u'softener', u'specialized_diet', u'specialized_diet_exclude_dairy',
    u'specialized_diet_exclude_nightshades',
    u'specialized_diet_exclude_refined_sugars', u'specialized_diet_fodmap',
    u'specialized_diet_halaal',
    u'specialized_diet_i_do_not_eat_a_specialized_diet',
    u'specialized_diet_kosher', u'specialized_diet_modified_paleo_diet',
    u'specialized_diet_other_restrictions_not_described_here',
    u'specialized_diet_paleodiet_or_primal_diet',
    u'specialized_diet_raw_food_diet', u'specialized_diet_unspecified',
    u'specialized_diet_westenprice_or_other_lowgrain_low_processed_fo',
    u'specialized_diet_westenprice_or_other_lowgrain_low_processed_food_diet',
    u'state', u'subset_age', u'subset_antibiotic_history', u'subset_bmi',
    u'subset_diabetes', u'subset_healthy', u'subset_ibd',
    u'sugar_sweetened_drink_frequency', u'sugary_sweets_frequency',
    u'surf_board_type', u'surf_frequency', u'surf_loal_break_frequency',
    u'surf_local_break', u'surf_shower_frequency', u'surf_stance',
    u'surf_sunscreen', u'surf_sunscreen_frequency', u'surf_travel_distance',
    u'surf_travel_frequency', u'surf_wax', u'surf_weetsuit', u'survey_id',
    u'taxon_id', u'teethbrushing_frequency', u'thyroid', u'title',
    u'toilet_water_access', u'tonsils_removed', u'types_of_plants',
    u'vegetable_frequency', u'vioscreen_a_bev', u'vioscreen_a_cal',
    u'vioscreen_acesupot', u'vioscreen_activity_level', u'vioscreen_add_sug',
    u'vioscreen_addsugar', u'vioscreen_adsugtot', u'vioscreen_age',
    u'vioscreen_alanine', u'vioscreen_alcohol', u'vioscreen_alcohol_servings',
    u'vioscreen_alphacar', u'vioscreen_alphtoce', u'vioscreen_alphtoco',
    u'vioscreen_arginine', u'vioscreen_ash', u'vioscreen_aspartam',
    u'vioscreen_aspartic', u'vioscreen_avcarb', u'vioscreen_bcodeid',
    u'vioscreen_betacar', u'vioscreen_betacryp', u'vioscreen_betaine',
    u'vioscreen_betatoco', u'vioscreen_biochana', u'vioscreen_bmi',
    u'vioscreen_caffeine', u'vioscreen_calcium', u'vioscreen_calcium_avg',
    u'vioscreen_calcium_dose', u'vioscreen_calcium_freq',
    u'vioscreen_calcium_from_dairy_servings', u'vioscreen_calcium_servings',
    u'vioscreen_calories', u'vioscreen_carbo', u'vioscreen_cholest',
    u'vioscreen_choline', u'vioscreen_clac9t11', u'vioscreen_clat10c12',
    u'vioscreen_copper', u'vioscreen_coumest', u'vioscreen_cystine',
    u'vioscreen_d_cheese', u'vioscreen_d_milk', u'vioscreen_d_tot_soym',
    u'vioscreen_d_total', u'vioscreen_d_yogurt', u'vioscreen_daidzein',
    u'vioscreen_database', u'vioscreen_delttoco', u'vioscreen_discfat_oil',
    u'vioscreen_discfat_sol', u'vioscreen_dob', u'vioscreen_eer',
    u'vioscreen_email', u'vioscreen_erythr', u'vioscreen_f_citmlb',
    u'vioscreen_f_nj_citmlb', u'vioscreen_f_nj_other', u'vioscreen_f_nj_total',
    u'vioscreen_f_other', u'vioscreen_f_total', u'vioscreen_fat',
    u'vioscreen_fiber', u'vioscreen_fibh2o', u'vioscreen_fibinso',
    u'vioscreen_finished', u'vioscreen_fish_servings', u'vioscreen_fol_deqv',
    u'vioscreen_fol_nat', u'vioscreen_fol_syn', u'vioscreen_formontn',
    u'vioscreen_fried_fish_servings', u'vioscreen_fried_food_servings',
    u'vioscreen_frt5_day', u'vioscreen_frtsumm', u'vioscreen_fructose',
    u'vioscreen_fruit_servings', u'vioscreen_g_nwhl', u'vioscreen_g_total',
    u'vioscreen_g_whl', u'vioscreen_galactos', u'vioscreen_gammtoco',
    u'vioscreen_gender', u'vioscreen_genistn', u'vioscreen_glac',
    u'vioscreen_gltc', u'vioscreen_glucose', u'vioscreen_glutamic',
    u'vioscreen_glycine', u'vioscreen_glycitn', u'vioscreen_grams',
    u'vioscreen_hei2010_dairy', u'vioscreen_hei2010_empty_calories',
    u'vioscreen_hei2010_fatty_acids', u'vioscreen_hei2010_fruit',
    u'vioscreen_hei2010_greens_beans', u'vioscreen_hei2010_protien_foods',
    u'vioscreen_hei2010_refined_grains', u'vioscreen_hei2010_score',
    u'vioscreen_hei2010_sea_foods_plant_protiens', u'vioscreen_hei2010_sodium',
    u'vioscreen_hei2010_veg', u'vioscreen_hei2010_whole_fruit',
    u'vioscreen_hei2010_whole_grains', u'vioscreen_hei_drk_g_org_veg_leg',
    u'vioscreen_hei_fruit', u'vioscreen_hei_grains',
    u'vioscreen_hei_meat_beans',
    u'vioscreen_hei_milk', u'vioscreen_hei_non_juice_frt',
    u'vioscreen_hei_oils',
    u'vioscreen_hei_sat_fat', u'vioscreen_hei_score', u'vioscreen_hei_sodium',
    u'vioscreen_hei_sol_fat_alc_add_sug', u'vioscreen_hei_veg',
    u'vioscreen_hei_whl_grains', u'vioscreen_height', u'vioscreen_histidin',
    u'vioscreen_inositol', u'vioscreen_iron', u'vioscreen_isoleuc',
    u'vioscreen_isomalt', u'vioscreen_joules', u'vioscreen_juice_servings',
    u'vioscreen_lactitol', u'vioscreen_lactose', u'vioscreen_legumes',
    u'vioscreen_leucine', u'vioscreen_line_gi',
    u'vioscreen_low_fat_dairy_serving',
    u'vioscreen_lutzeax', u'vioscreen_lycopene', u'vioscreen_lysine',
    u'vioscreen_m_egg', u'vioscreen_m_fish_hi', u'vioscreen_m_fish_lo',
    u'vioscreen_m_frank', u'vioscreen_m_meat', u'vioscreen_m_mpf',
    u'vioscreen_m_nutsd', u'vioscreen_m_organ', u'vioscreen_m_poult',
    u'vioscreen_m_soy', u'vioscreen_magnes', u'vioscreen_maltitol',
    u'vioscreen_maltose', u'vioscreen_mangan', u'vioscreen_mannitol',
    u'vioscreen_methhis3', u'vioscreen_methion', u'vioscreen_mfa141',
    u'vioscreen_mfa161', u'vioscreen_mfa181', u'vioscreen_mfa201',
    u'vioscreen_mfa221', u'vioscreen_mfatot', u'vioscreen_multi_calcium_avg',
    u'vioscreen_multi_calcium_dose', u'vioscreen_multivitamin',
    u'vioscreen_multivitamin_freq', u'vioscreen_natoco', u'vioscreen_nccglbr',
    u'vioscreen_nccglgr', u'vioscreen_niacin', u'vioscreen_niacineq',
    u'vioscreen_nitrogen', u'vioscreen_non_fried_fish_servings',
    u'vioscreen_nutrient_recommendation', u'vioscreen_omega3',
    u'vioscreen_oxalic',
    u'vioscreen_oxalicm', u'vioscreen_pantothe', u'vioscreen_pectins',
    u'vioscreen_pfa182', u'vioscreen_pfa183', u'vioscreen_pfa184',
    u'vioscreen_pfa204', u'vioscreen_pfa205', u'vioscreen_pfa225',
    u'vioscreen_pfa226', u'vioscreen_pfatot', u'vioscreen_phenylal',
    u'vioscreen_phosphor', u'vioscreen_phytic', u'vioscreen_pinitol',
    u'vioscreen_potass', u'vioscreen_procdate', u'vioscreen_proline',
    u'vioscreen_protanim', u'vioscreen_protein', u'vioscreen_protocol',
    u'vioscreen_protveg', u'vioscreen_questionnaire', u'vioscreen_recno',
    u'vioscreen_retinol', u'vioscreen_rgrain', u'vioscreen_ribofla',
    u'vioscreen_sacchar', u'vioscreen_salad_vegetable_servings',
    u'vioscreen_satoco', u'vioscreen_scf', u'vioscreen_scfv',
    u'vioscreen_selenium', u'vioscreen_serine', u'vioscreen_sfa100',
    u'vioscreen_sfa120', u'vioscreen_sfa140', u'vioscreen_sfa160',
    u'vioscreen_sfa170', u'vioscreen_sfa180', u'vioscreen_sfa200',
    u'vioscreen_sfa220', u'vioscreen_sfa40', u'vioscreen_sfa60',
    u'vioscreen_sfa80', u'vioscreen_sfatot', u'vioscreen_sodium',
    u'vioscreen_sorbitol', u'vioscreen_srvid', u'vioscreen_starch',
    u'vioscreen_started', u'vioscreen_subject_id', u'vioscreen_sucpoly',
    u'vioscreen_sucrlose', u'vioscreen_sucrose', u'vioscreen_sweet_servings',
    u'vioscreen_tagatose', u'vioscreen_tfa161t', u'vioscreen_tfa181t',
    u'vioscreen_tfa182t', u'vioscreen_tgrain', u'vioscreen_thiamin',
    u'vioscreen_threonin', u'vioscreen_time', u'vioscreen_totaltfa',
    u'vioscreen_totcla', u'vioscreen_totfolat', u'vioscreen_totsugar',
    u'vioscreen_tryptoph', u'vioscreen_tyrosine', u'vioscreen_user_id',
    u'vioscreen_v_drkgr', u'vioscreen_v_orange', u'vioscreen_v_other',
    u'vioscreen_v_potato', u'vioscreen_v_starcy', u'vioscreen_v_tomato',
    u'vioscreen_v_total', u'vioscreen_valine', u'vioscreen_veg5_day',
    u'vioscreen_vegetable_servings', u'vioscreen_vegsumm', u'vioscreen_visit',
    u'vioscreen_vita_iu', u'vioscreen_vita_rae', u'vioscreen_vita_re',
    u'vioscreen_vitb12', u'vioscreen_vitb6', u'vioscreen_vitc',
    u'vioscreen_vitd', u'vioscreen_vitd2', u'vioscreen_vitd3',
    u'vioscreen_vitd_iu', u'vioscreen_vite_iu', u'vioscreen_vitk',
    u'vioscreen_water', u'vioscreen_weight', u'vioscreen_wgrain',
    u'vioscreen_whole_grain_servings',
    u'vioscreen_xylitol', u'vioscreen_zinc',
    u'vitamin_b_supplement_frequency',
    u'vitamin_d_supplement_frequency', u'vivid_dreams', u'weight_cat',
    u'weight_change', u'weight_kg', u'weight_units', u'whole_eggs',
    u'whole_grain_frequency'
]


def get_qiita_client():
    if config.debug:
        class _mock:
            def get(self, *args, **kwargs):
                return {'categories': AG_DEBUG_OBSERVED_CATEGORIES}

            def http_patch(self, *args, **kwargs):
                return 'okay'

        qclient = _mock()
    else:
        # interface for making HTTP requests against Qiita
        qclient = QiitaClient(':'.join([config.qiita_host, config.qiita_port]),
                              config.qiita_client_id,
                              config.qiita_client_secret,
                              config.qiita_certificate)

        # we are monkeypatching to use qclient's internal machinery
        # and to fix the broken HTTP patch
        qclient.http_patch = functools.partial(qclient._request_retry,
                                               requests.patch)
    return qclient


class BarcodeUtilHelper(object):
    def get_ag_details(self, barcode):
        ag_details = db.getAGBarcodeDetails(barcode)
        _, failures = db.pulldown([barcode], [])

        if len(ag_details) == 0 and failures:
            div_id = "no_metadata"
            message = "Cannot retrieve metadata: %s" % failures[barcode]
        elif len(ag_details) > 0:
            for col, val in ag_details.iteritems():
                if val is None:
                    ag_details[col] = ''
            ag_details['other_checked'] = ''
            ag_details['overloaded_checked'] = ''
            ag_details['moldy_checked'] = ''
            ag_details['login_user'] = ag_details['name']
            if ag_details['moldy'] == 'Y':
                ag_details['moldy_checked'] = 'checked'
            if ag_details['overloaded'] == 'Y':
                ag_details['overloaded_checked'] = 'checked'
            if ag_details['other'] == 'Y':
                ag_details['other_checked'] = 'checked'

            survey_id = db.get_barcode_survey(barcode)

            # it has all sample details
            # (sample time, date, site)
            if failures:
                div_id = "no_metadata"
                message = "Cannot retrieve metadata: %s" % failures[barcode]
                ag_details['email_type'] = "-1"
            elif (survey_id is None and ag_details['environment_sampled']) \
                    or survey_id in survey_type:
                div_id = "verified"
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
                           "never happen. Please notify "
                           "someone on the database crew.")
                ag_details['email_type'] = "-1"
        else:
            # TODO: Stefan Janssen: I cannot see how this case should ever be
            # reached, since failures will be set to 'Unknown reason' at the
            # outmost.
            div_id = "not_assigned"
            message = ("In American Gut project group but no "
                       "American Gut info for barcode")
            ag_details['email_type'] = "-1"
        return div_id, message, ag_details

    def update_ag_barcode(self, barcode, login_user, login_email, email_type,
                          sent_date, send_mail, sample_date, sample_time,
                          other_text):
        email_msg = ag_update_msg = None
        if all([send_mail is not None, login_email is not None,
                login_email != '']):
            subject, body_message = self._build_email(
                login_user, barcode, email_type, sample_date, sample_time)
            if body_message != '':
                sent_date = datetime.now()
                email_msg = ("Sent email successfully to kit owner %s" %
                             login_email)
                try:
                    send_email(body_message, subject, login_email, html=True)
                except:  # noqa
                    email_msg = ("Email sending to (%s) failed (barcode: %s)!"
                                 "<br/>" % (login_email, barcode))
        sample_issue = self.get_argument('sample_issue', [])
        moldy = overloaded = other = 'N'
        if 'moldy' in sample_issue:
            moldy = 'Y'
        if 'overloaded' in sample_issue:
            overloaded = 'Y'
        if 'other' in sample_issue:
            other = 'Y'
        ag_update_msg = ("Barcode %s AG info was successfully updated" %
                         barcode)
        try:
            db.updateAKB(barcode, moldy, overloaded, other, other_text,
                         sent_date)
        except:  # noqa
            ag_update_msg = ("Barcode %s AG update failed!!!" % barcode)

        return email_msg, ag_update_msg

    def _build_email(self, login_user, barcode, email_type,
                     sample_date, sample_time):
        subject = body_message = u""

        if email_type in ('0', '-1'):
            subject = u'ACTION REQUIRED - Assign your samples in American Gut'
            body_message = u"""
<html>
<body>
<p>Dear {name},</p>
<p>We have recently received your sample barcode: {barcode}, but we cannot
process your sample until the following steps have been completed online.
Please ensure that you have completed <b>both</b> steps outlined below:</p>
<ol>
<li><b>Submit your consent form and survey-<i>if you have already done these
please proceed to step 2 below.</i></b><br/>For human samples, the consent form
is mandatory. Even if you elect not to answer the questions on the survey,
please click through and submit the survey in order to ensure we receive your
completed consent form.</li>
<li><b>Assign your sample(s) to your survey(s)</b><br/>This step is critical as
it connects your consent form to your sample. We cannot legally work with your
sample until this step has been completed.</li>
</ol>
<p>To assign your sample to your survey:</p>
<ul>
<li>Log into your account and click the &quot;Assign&quot; button at the bottom
of the left-hand navigation menu. This will bring you to a screen with the
heading &quot;Choose your sample source&quot;.</li>
<li>Click on the name of the participant that the sample belongs to.</li>
<li>Fill out the required fields and submit.</li>
</ul>
<p>
The American Gut participant website is located at<br/>
<a href='https://microbio.me/americangut'>https://microbio.me/americangut</a>
<br/>The British Gut participant website is located at<br/>
<a href='https://microbio.me/britishgut'>https://microbio.me/britishgut</a>
<br/>If you have any questions, please contact us at
<a href='mailto:info@americangut.org'>info@americangut.org</a>.</p>
<p>Thank you,<br/>
American Gut Team</p>
</body>
</html>"""

            body_message = body_message.format(name=login_user,
                                               barcode=barcode)
        elif email_type == '1':
            subject = (u'American Gut Sample with Barcode %s is Received.'
                       % barcode)
            body_message = u"""<html><body><p>
Dear {name},</p>

<p>We have recently received your sample with barcode {barcode} dated
{sample_date} {sample_time} and we have begun processing it.  Please see our
FAQ section for when you can expect results.<br/>
(<a href='https://microbio.me/AmericanGut/faq/#faq4'
>https://microbio.me/AmericanGut/faq/#faq4</a>)</p>

<p>Thank you for your participation!</p>

<p>--American Gut Team--</p></body></html>
"""
            body_message = body_message.format(name=login_user,
                                               barcode=barcode,
                                               sample_date=sample_date,
                                               sample_time=sample_time)
        else:
            raise RuntimeError("Unknown email type passed: %s" % email_type)

        return subject, body_message


def align_with_qiita_categories(samples, categories,
                                failure_value='pulldown-issue',
                                omitted_value='Missing: Not provided'):
    """Obtain sample metadata, and subset to those categories present in Qiita

    Parameters
    ----------
    samples : list of str
        The samples to get metadata for
    categories : Iterable of str
        The categories to align against
    failure_value : str, optional
        The default value to use for a sample that failed pulldown.
    omitted_value : str, optional
        The default value to use for a variable not represented either in Qiita
        or the extracted metadata.

    Notes
    -----
    The env_package variable for failures will be autofilled with "Air" per a
    request from Gail.

    Any variable in extract metadata that is not represented in Qiita will be
    silently omitted (e.g., PM_USEFUL).

    Any variable in Qiita that is not represented in the extracted metadata
    (e.g., qiita_empo_1) will be filled with the omitted_value.

    Returns
    -------
    dict of dict
        A stucture of the metadata per sample. {sample-id: {category: value}}
    """
    surveys, failures = db.pulldown(samples)

    # pulldown returns a per-survey (e.g., primary, fermented food, etc) tab
    # delimited file. What we're doing here is de-serializing those data into
    # per survey DataFrames, and then concatenating them together such that
    # each sample ID is a row, each sample ID is only represented once, and the
    # columns correspond to variables from each survey type.
    surveys_as_df = []
    for _, v in sorted(surveys.items()):
        surveys_as_df.append(pd.read_csv(StringIO.StringIO(v), sep='\t',
                                         dtype=str).set_index('sample_name'))

    surveys_as_df = pd.concat(surveys_as_df, axis=1)

    # oddly, it seems possible in the present pulldown code for an ID to be
    # successful and a failure
    failures = {f for f in failures if f not in surveys_as_df.index}

    # columns in Qiita are lower case
    surveys_as_df.columns = [c.lower() for c in surveys_as_df.columns]

    # subset the frame to the overlapping columns
    categories = set(categories)
    column_overlap = surveys_as_df.columns.intersection(categories)
    surveys_as_df = surveys_as_df[column_overlap]

    # missing categories are those in qiita but not in the pulldown
    missing_categories = categories - set(column_overlap)

    # represent failures in the dataframe
    failures_as_df = pd.DataFrame(index=list(failures),
                                  columns=surveys_as_df.columns)
    failures_as_df.fillna(failure_value, inplace=True)
    failures_as_df['env_package'] = 'Air'  # per request from Gail

    # append will add rows aligned on the columns
    surveys_as_df = surveys_as_df.append(failures_as_df)

    # represent missing entries in the dataframe
    missing = pd.DataFrame(index=list(surveys_as_df.index),
                           columns=sorted(missing_categories))
    missing.fillna(omitted_value, inplace=True)

    # join will add columns aligned on the index
    surveys_as_df = surveys_as_df.join(missing)

    return surveys_as_df.to_dict(orient='index')


@set_access(['Scan Barcodes'])
class PushQiitaHandler(BaseHandler):
    executor = concurrent.futures.ThreadPoolExecutor(5)
    study_id = config.qiita_study_id
    qclient = get_qiita_client()

    @concurrent.run_on_executor
    def _push_to_qiita(self, study_id, samples):
        # TODO: add a mutex or block to ensure a single call process at a time
        cats = self.qclient.get('/api/v1/study/%s/samples/info' % study_id)
        cats = cats['categories']

        samples = align_with_qiita_categories(samples, cats)
        data = json_encode(samples)

        return self.qclient.http_patch('/api/v1/study/%s/samples' % study_id,
                                       data=data)

    @authenticated
    def get(self):
        barcodes = db.get_unsent_barcodes_from_qiita_buffer()
        status = db.get_send_qiita_buffer_status()
        dat = {'status': status, "barcodes": barcodes}
        self.write(json_encode(dat))
        self.finish()

    @authenticated
    @gen.coroutine
    def post(self):
        barcodes = db.get_unsent_barcodes_from_qiita_buffer()
        if not barcodes:
            return

        # certainly not a perfect mutex, however tornado is single threaded
        status = db.get_send_qiita_buffer_status()
        if status in ['Failed!', 'Pushing...']:
            return

        db.set_send_qiita_buffer_status("Pushing...")

        try:
            yield self._push_to_qiita(self.study_id, barcodes)
        except:  # noqa
            db.set_send_qiita_buffer_status("Failed!")
        else:
            db.mark_barcodes_sent_to_qiita(barcodes)
            db.set_send_qiita_buffer_status("Idle")


@set_access(['Scan Barcodes'])
class BarcodeUtilHandler(BaseHandler, BarcodeUtilHelper):

    @authenticated
    def get(self):
        barcode = self.get_argument('barcode', None)
        if barcode is None:
            self.render("barcode_util.html", div_and_msg=None,
                        barcode_projects=[], parent_project=None,
                        project_names=[], barcode=None, email_type=None,
                        barcode_info=None, proj_barcode_info=None, msgs=None,
                        currentuser=self.current_user)
            return
        # gather info to display
        barcode_details = db.get_barcode_details(barcode)
        if len(barcode_details) == 0:
            div_id = "invalid_barcode"
            message = ("Barcode %s does not exist in the database" %
                       barcode)
            self.render("barcode_util.html",
                        div_and_msg=(div_id, message, barcode),
                        barcode_projects=[], parent_project=None,
                        project_names=[],
                        barcode=barcode, email_type=None,
                        barcode_info=None, proj_barcode_info=None,
                        msgs=None, currentuser=self.current_user)
            return

        barcode_projects, parent_project = db.getBarcodeProjType(
            barcode)
        project_names = db.getProjectNames()

        # barcode exists get general info
        # TODO (Stefan Janssen): check spelling of "received", i.e. tests in
        # the template check for 'Recieved'. I think the logic is broken due
        # to that.
        if barcode_details['status'] is None:
            barcode_details['status'] = 'Received'
        if barcode_details['biomass_remaining'] is None:
            barcode_details['biomass_remaining'] = 'Unknown'
        if barcode_details['sequencing_status'] is None:
            barcode_details['sequencing_status']
        if barcode_details['obsolete'] is None:
            barcode_details['obsolete'] = 'N'
        div_id = message = ""
        if (barcode_details['obsolete'] == "Y"):
            # the barcode is obsolete
            div_id = "obsolete"
            # TODO: Stefan: why is that set here, as far as I see, this
            # message will in all cases be overwritten!
            message = "Barcode is Obsolete"
        # get project info for div
        ag_details = []
        if parent_project == 'American Gut':
            div_id, message, ag_details = self.get_ag_details(barcode)
        else:
            div_id = "verified"
            message = "Barcode Info is correct"
        div_and_msg = (div_id, message, barcode)
        self.render("barcode_util.html", div_and_msg=div_and_msg,
                    barcode_projects=barcode_projects,
                    parent_project=parent_project,
                    project_names=project_names,
                    barcode=barcode, email_type=None,
                    barcode_info=barcode_details,
                    proj_barcode_info=ag_details, msgs=None,
                    currentuser=self.current_user)

    @authenticated
    def post(self):
        barcode = self.get_argument('barcode')
        postmark_date = self.get_argument('postmark_date', None)
        scan_date = self.get_argument('scan_date', None)
        biomass_remaining_value = self.get_argument('biomass_remaining_value',
                                                    None)
        sequencing_status = self.get_argument('sequencing_status', None)
        obsolete_status = self.get_argument('obsolete_status', None)
        projects = set(self.get_arguments('project'))
        sent_date = self.get_argument('sent_date', None)
        login_user = self.get_argument('login_user',
                                       'American Gut participant')
        send_mail = self.get_argument('send_mail', None)
        login_email = self.get_argument('login_email', None)
        other_text = self.get_argument('other_text', None)
        email_type = self.get_argument('email_type', None)
        sample_time = self.get_argument('sample_time', None)
        sample_date = self.get_argument('sample_date', None)
        # now we collect data and update based on forms
        # first update general barcode info
        # Set to non to make sure no conflicts with new date typing in DB
        if not postmark_date:
            postmark_date = None
        if not scan_date:
            scan_date = None
        try:
            db.updateBarcodeStatus('Received',
                                   postmark_date,
                                   scan_date, barcode,
                                   biomass_remaining_value,
                                   sequencing_status,
                                   obsolete_status)
            gen_update_msg = "Barcode %s general details updated" % barcode
        except:  # noqa
            gen_update_msg = "Barcode %s general details failed" % barcode

        email_msg = ag_update_msg = project_msg = None
        exisiting_proj, parent_project = db.getBarcodeProjType(
            barcode)
        # This WILL NOT let you remove a sample from being in AG if it is
        # part of AG to begin with
        exisiting_proj = set(exisiting_proj.split(', '))
        if exisiting_proj != projects:
            try:
                add_projects = projects.difference(exisiting_proj)
                rem_projects = exisiting_proj.difference(projects)
                db.setBarcodeProjects(barcode, add_projects, rem_projects)
                project_msg = "Project successfully changed"
            except:  # noqa
                project_msg = "Error changing project"

            new_proj, parent_project = db.getBarcodeProjType(barcode)
        if parent_project == 'American Gut':
            db.push_barcode_to_qiita_buffer(barcode)

            email_msg, ag_update_msg = self.update_ag_barcode(
                barcode, login_user, login_email, email_type, sent_date,
                send_mail, sample_date, sample_time, other_text)

        self.render("barcode_util.html", div_and_msg=None,
                    barcode_projects=[],
                    parent_project=None,
                    project_names=[], barcode=None,
                    email_type=None,
                    barcode_info=None, proj_barcode_info=None,
                    msgs=(gen_update_msg, email_msg, ag_update_msg,
                          project_msg),
                    currentuser=self.current_user)
