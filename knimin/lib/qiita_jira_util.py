# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from collections import defaultdict

from tornado.escape import json_encode

from knimin import jira_handler, qiita_client, db


def _format_sample_id(sample_id, plate_id, row, col):
    """Formats the name of the samples to include the plate and well

    Parameters
    ----------
    sample_id : str
        the sample id
    plate_id : int
        The plate id
    row : int
        The row # of the well
    col : int
        The col # of the well
    """
    # Fix for the fact that we start indexing at 0
    col = col + 1
    # Use letters only for the first 26 rows of the plate
    if row < 26:
        row = chr(ord('A') + row)
        well = "%s%s" % (row, col)
    else:
        well = "%s.%s" % (row, col)
    return "%s.%s.%s" % (sample_id, plate_id, well)


def _update_qiita_samples(study_id, blanks, replicates):
    """Updates the qiita study with blanks and technical replicates

    Parameters
    ----------
    study_id : int
        The study id
    blanks : list of (str, int, int, int)
        For each blank to add, the blank name, plate, row and column
    replicates : list of (str, int, int, int)
        For each technical replicate, the sample id, plate, row and column

    Raises
    ------
    ValueError
        If there is any problem accessing the Qiita REST API
    """
    # Existing metadata_categories
    sc, categories = qiita_client.get(
        '/api/v1/study/%s/samples/info' % study_id)
    if sc != 200:
        msg = categories['message'] if categories else 'No error specified'
        raise ValueError(
            "Can't retrieve study (%s) metadata categories from Qiita: %s %s"
            % (study_id, sc, msg))
    categories = categories['categories']

    # Get the current metadata
    sc, md = qiita_client.get('/api/v1/study/%s/samples/categories=%s'
                              % (study_id, ','.join(categories)))
    if sc != 200:
        msg = md['message'] if md else 'No error specified'
        raise ValueError(
            "Can't retrieve study (%s) metadata from Qiita: %s %s"
            % (study_id, sc, msg))

    new_md = {}
    # This is the blanks metadata, mark all categories as not applicable
    blanks_md = {c: 'Not applicable' for c in categories}
    # Construct the metadata for the blanks
    for sample_id, plate, row, col in blanks:
        # We need to make sure that the blanks are also pre-fixed with the
        # study id. Otherwise, is both blanks and study samples are being
        # added at once, the study samples will be prefixed twice
        new_sample_id = "%s.%s" % (
            study_id, _format_sample_id(sample_id, plate, row, col))
        new_md[new_sample_id] = blanks_md

    # Construct the metadata for the technical replicates
    for sample_id, plate, row, col in replicates:
        new_sample_id = _format_sample_id(sample_id, plate, row, col)
        # Use the metadata of the original sample
        new_md[new_sample_id] = {
            c: v for c, v in zip(categories, md['samples'][sample_id])}

    # Making sure that there is something to send
    if new_md:
        sc, msg = qiita_client.patch('/api/v1/study/%s/samples' % (study_id),
                                     data=json_encode(new_md))
        if sc not in (200, 201):
            msg = msg['message'] if msg else 'No error specified'
            raise ValueError("Can't create samples in Qiita: %s %s"
                             % (sc, msg))


def _create_kl_jira_project(jira_user, jira_template, study_id, title):
    # Generate the Jira key
    key = '%s%d' % (
        ''.join([k[0] for k in jira_template.split(' ') if k]).upper(),
        study_id)

    # Generate the Jira key
    jira_project = jira_handler.create_project(
        key=key, name=title, assignee=jira_user,
        template_name=jira_template)

    # Generate the 7 issues in the Jira project
    summaries = ["1 - Project initiation", "2 - Experimental design",
                 "3 - Sample receipt", "4 - Library preparation",
                 "5 - Molecular characterization and data transfer",
                 "6 - Data analysis",
                 "7 - Manuscript preparation and submission"]
    descriptions = [ISSUE1_DESC, ISSUE2_DESC, ISSUE3_DESC, ISSUE4_DESC,
                    ISSUE5_DESC, ISSUE6_DESC, ISSUE7_DESC]

    issues = [{"project": {"key": key}, "summary": s, "description": d,
               "issuetype": {"name": "Task"}}
              for s, d, in zip(summaries, descriptions)]

    jira_handler.create_issues(issues, prefetch=False)

    return jira_project


def create_study(title, abstract, description, alias, qiita_user,
                 qiita_pi, qiita_lp, jira_user,
                 jira_template="Task management"):
    """Creates a study in Qiita, Jira and LabAdmin

    Parameters
    ----------
    title: str
        The study title
    abstract: str
        The study abstract
    description : str
        The study description
    alias: str
        The study alias
    qiita_user : str
        The Qiita user that will own the study
    qiita_pi : dict of str
        The Qiita study Principal Investigator name, affiliation,
        and (optionally) email
    qiita_lp : dict of str
        The Qiita study lab person name, affiliation and (optionally) email
    jira_user : str
        The JIRA user that will lead the project
    jira_template : str, optional
        The JIRA template name

    Returns
    -------
    int
        The study ID

    Raises
    ------
    ValueError
        If there is any problem creating the Qiita person or the Qiita study
    """
    # Step 1: Create the study in Qiita
    # Make sure that the qiita_pi and qiita_lp exist in Qiita
    # We will assume that if the email is given, then the person needs to be
    # created in qiita
    for val in [qiita_pi, qiita_lp]:
        if 'email' in val:
            status_code, msg = qiita_client.post('/api/v1/person', data=val)
            if status_code != 201:
                raise ValueError('Error creating person "%s": %s'
                                 % (val['name'], msg['message']))

    # Step 1.2: Create the study itself
    payload = {'title': title, 'study_abstract': abstract,
               'study_description': description, 'study_alias': alias,
               'owner': qiita_user,
               'contacts': {
                    'principal_investigator': [qiita_pi['name'],
                                               qiita_pi['affiliation']],
                    'lab_person': [qiita_lp['name'], qiita_lp['affiliation']]}}
    status_code, data = qiita_client.post("/api/v1/study", data=payload,
                                          as_json=True)
    if status_code != 201:
        raise ValueError("Error creating Qiita study: %s" % data['message'])
    study_id = data['id']

    # Step 2: Create the study in JIRA
    jira_project = _create_kl_jira_project(jira_user, jira_template,
                                           study_id, title)

    # Step 3: Create the study locally
    db.create_study(study_id, title, alias, jira_project['projectKey'])

    return study_id


def sync_qiita_study_samples(study_id):
    """Syncs the DB with the samples in the Qiita study

    Parameters
    ----------
    study_id : int
        The id of the study to sync
    """
    sc, samples = qiita_client.get('/api/v1/study/%s/samples' % study_id)
    if sc != 200:
        msg = samples['message'] if samples else 'No error specified'
        raise ValueError(
            "Can't retrieve samples from Qiita for study (%s): %s %s"
            % (study_id, sc, msg))

    db.set_study_samples(study_id, samples)


def extract_sample_plates(sample_plate_ids, email, robot, kit_lot,
                          tool, notes=None):
    """Stores the extraction information for the given sample_plates

    Updates Qiita and Jira accordingly

    Parameters
    ----------
    sample_plate_ids : list of int
        The sample plates being extracted
    email : str
        The email of the user preparing the extraction
    robot : str
        The name of the robot used for extraction
    kit_lot : str
        The kit lot used for extraction
    tool : str
        The name of the tool used for extraction
    notes : str, optional
        Notes added to the extracted plates

    Returns
    -------
    list of int
        The extracted DNA plates ids
    """
    # Store the DNA extraction information on the DB
    dna_plates = db.extract_sample_plates(sample_plate_ids, email, robot,
                                          kit_lot, tool, notes)

    study_br = defaultdict(lambda: {'blanks': [], 'replicates': []})

    for dna_plate_id, sample_plate_id in zip(dna_plates, sample_plate_ids):
        sample_plate = db.read_sample_plate(sample_plate_id)

        # Retrieve the blank samples from the plate
        blanks = [(s_id, dna_plate_id, row, col)
                  for s_id, row, col in db.get_blanks_from_sample_plate(
                    sample_plate_id)]

        if blanks:
            for study in sample_plate['studies']:
                study_br[study]['blanks'].extend(blanks)

        # Retrieve the technical replicates from the plate
        replicates = db.get_replicates_from_sample_plate(sample_plate_id)
        for sample_id in replicates:
            sample = db.read_sample(sample_id)
            wells = replicates[sample_id]
            study_br[sample['study_id']]['replicates'].extend(
                [(sample_id, dna_plate_id, well[0], well[1])
                 for well in wells])

    for study_id in study_br:
        # Need to update Qiita with the blanks and replicates
        _update_qiita_samples(study_id, study_br[study_id]['blanks'],
                              study_br[study_id]['replicates'])

        # Need to update Jira - the issue to update is issue 4
        study = db.read_study(study_id)
        issue_key = '%s-4' % study['jira_id']
        jira_handler.add_comment(
            issue_key, "Samples have been plated")

    jira_handler
    return dna_plates


def prepare_targeted_libraries(plate_links, email, robot, tm300tool,
                               tm50tool, mastermix_lot, water_lot):
    """Stores the targeted plate library information

    Parameters
    ----------
    plate_links : list of dicts
        A list of {'dna_plate_id': int, 'primer_plate_id': int} linking
        a DNA plate with the primer plate used
    email : str
        The email of the user doing the library prep
    robot : str
        The name of the robot used
    tm300tool : str
        The name of the TM300-8 tool used
    tm50tool : str
        The name of the TM50-8 tool used
    mastermix_lot : str
        The mastermix lot used
    water_lot : str
        The water lot used

    Returns
    -------
    list of int
        The new target_plate ids created
    """
    targeted_plate_ids = db.prepare_targeted_libraries(
        plate_links, email, robot, tm300tool, tm50tool,
        mastermix_lot, water_lot)

    studies = []
    for val in plate_links:
        sample_plate = db.read_sample_plate(
            db.read_dna_plate(val['dna_plate_id'])['sample_plate_id'])

        studies.extend(sample_plate['studies'])

    for study_id in set(studies):
        study = db.read_study(study_id)
        issue_key = '%s-4' % study['jira_id']
        jira_handler.add_comment(
            issue_key, "Target gene libraries have been prepared")

    return targeted_plate_ids


def create_sequencing_run(pool_id, email, sequencer, reagent_type,
                          reagent_lot):
    """Stores the sequencing run information

    Parameters
    ----------
    pool_id : int
        The pool being sequenced
    email : str
        The email of the user preparing the run
    sequencer : id
        The sequencer id
    reagent_type : str
        The reagent type
    reagent_lot : str
        The reagent lot

    Returns
    -------
    int
        The run id
    """
    run_id = db.create_sequencing_run(pool_id, email, sequencer, reagent_type,
                                      reagent_lot)
    studies = []
    for targeted_pool in db.read_pool(pool_id)['targeted_pools']:
        targeted_plate = db.read_targeted_plate(
            targeted_pool['targeted_plate_id'])
        dna_plate = db.read_dna_plate(targeted_plate['dna_plate_id'])
        sample_plate = db.read_sample_plate(dna_plate['sample_plate_id'])
        studies.extend(sample_plate['studies'])

    for study_id in set(studies):
        study = db.read_study(study_id)
        issue_key = '%s-4' % study['jira_id']
        jira_handler.add_comment(
            issue_key, "Pools have been sent for sequencing")

    return run_id


ISSUE1_DESC = """
When this step is complete, we will have:

- the general concept of the project
- the name and contact of the lead person
- names and contacts of internal and external collaborators who will form the\
 team
- funding sources with indexes where applicable
"""


ISSUE2_DESC = """
When task is complete there will be a powerpoint or pdf that clearly describes:

goal of project
experimental design
# samples
# subjects
variables that will be analyzed (technical and biological)
potential pitfalls
plan for how the analysis will be done
"""


ISSUE3_DESC = """
When this task is complete we will have:

- inventory of the samples (number and kind)
- location of where the samples are
- information about whether and how the samples can be re-used
- contact information for the specific people involved in gathering, labeling\
 and shipping the samples
- sample manifest that is labeled exactly the same way the samples are
- if appropriate, an MTA allowing us to actually use the samples and/or\
 resulting data
"""


ISSUE4_DESC = """
When this task is complete we will have some or all of the following ready \
to run on instrument:

- 16S rRNA
- 18S rRNA
- ITS
- mitochondrial markers
- chloroplast markers
- shotgun metatranscriptomics
- shotgun metagenomics
- proteomics
- cells captured for culture
- stock cultures
"""


ISSUE5_DESC = """
When this task is complete, the data will have been generated on the \
appropriate instrument, and transferred to the correct file stores and \
uploaded to qiita and/or gnps as appropriate
"""


ISSUE6_DESC = """
When this step is complete, the data will have been analyzed and the \
following will be available:

- Internal accession numbers in qiita and/or gnps
- Figures and tables showing the results of the analysis
- Summary of the main results of the project
"""


ISSUE7_DESC = """
When this task is complete:

- External accession numbers (e.g. ebi or massive) will have been obtained
- Manuscript will be completely written and approved by all authors
- Manuscript will have been submitted to a journal
- Confirmation of receipt from the journal will have been logged
"""
