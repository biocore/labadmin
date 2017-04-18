# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from collections import defaultdict
from os.path import join
from functools import partial
from glob import glob
from os.path import basename
from shutil import copy

from tornado.escape import json_encode

from knimin import jira_handler, qiita_client, db, config
from knimin.lib.format import write_sample_sheet


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
    blanks : list of str
        The sample id of the blank
    replicates : list of (str, str)
        For each technical replicate, the new name and the original sample name

    Raises
    ------
    ValueError
        If there is any problem accessing the Qiita REST API
    """
    # Existing metadata_categories
    study_id = int(study_id)
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

    # This is the blanks metadata, mark all categories as not applicable
    blanks_md = {c: 'Not applicable' for c in categories}
    new_md = {sid: blanks_md for sid in blanks}

    # Construct the metadata for the technical replicates
    for new_sample_id, old_sample_id in replicates:
        # Use the metadata of the original sample
        new_md[new_sample_id] = dict(
            zip(categories, md['samples'][old_sample_id]))

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


def _assess_replicates(prep):
    """Renames the technical replciates in the prep information

    Parameters
    ----------
    prep : pandas.DataFrame
        The prep information

    Returns
    -------
    pandas.DataFrame, list of str
        The updated pandas dataframe and a list of replicates
    """
    counts = prep.sample_name.value_counts()
    replicates = counts[counts > 1].index.tolist()
    # Rename the samples by adding the plate id and the well.
    # Rename the column sample_name
    prep['original_sample_name'] = prep['sample_name'].copy()
    # Rename the samples as needed
    new_sample_ids = []
    for r in replicates:
        for i in prep[prep['original_sample_name'] == r].index:
            sample_id = _format_sample_id(
                prep.original_sample_name[i], prep.dna_plate_id[i],
                prep.row[i] - 1, prep.col[i] - 1)
            prep.loc[i, 'sample_name'] = sample_id
            new_sample_ids.append(sample_id)

    # It is ensured that the sample_name column contain unique IDs
    prep.set_index('sample_name', inplace=True, drop=True)

    return prep, new_sample_ids


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


def create_sequencing_run(pool_id, email, reagent_type, reagent_lot, platform,
                          instrument_model, assay, fwd_cycles, rev_cycles):
    """Stores the sequencing run information

    Parameters
    ----------
    pool_id : int
        The pool being sequenced
    email : str
        The email of the user preparing the run
    reagent_type : str
        The reagent type
    reagent_lot : str
        The reagent lot
    platform : str
        The sequencing platform (e.g., Illumina)
    instrument_model : str
        The model of the instrument (e.g., MiSeq)
    assay : str
        The assay used (e.g., Kapa Hyper Plus)
    fwd_cycles : int
        The number of forward cycles used.
    rev_cycles : int
        The number of reverse cycles used.

    Returns
    -------
    int
        The run id
    """
    # Store the information in the DB
    # Sequencer is hardcoded to None. This information may not be known at this
    # time but we can potentially retrieve this from the output sequencing
    # folder.
    run_id = db.create_sequencing_run(
        pool_id, email, None, reagent_type, reagent_lot, platform,
        instrument_model, assay, fwd_cycles, rev_cycles)

    run = db.read_sequencing_run(run_id)
    pool = db.read_pool(run['pool_id'])

    # To make sure that we generate the sample sheet correctly, we need to
    # assess the technical replicates at this time
    preps = db.generate_prep_information(run_id)
    for prep in preps:
        prep, replicates = _assess_replicates(prep)
        # Update qiita with blanks and replicates
        blanks = prep[prep.is_blank].index.tolist()
        replicates = [(sid, prep.original_sample_name[sid])
                      for sid in replicates if sid not in blanks]
        study_id = prep.study_id.iloc[0]
        _update_qiita_samples(study_id, blanks, replicates)

    # Write the sample sheet
    instrument_type = 'miseq' if instrument_model == 'MiSeq' else 'hiseq'
    run_type = "Target Gene" if pool['targeted_pools'] else "Shotgun"
    sample_information = None

    # TODO: Fill sample_information if the run is a HiSeq
    # TODO: I want to check with Greg the values for PI and contact
    contact_0_name = contact_0_email = pi_email = pi_name = 'TODO'
    output_fp = join(
        config.pm_sample_sheet_dir,
        "SampleSheet.%s.%s.csv" % (run['name'].replace(" ", "_"),
                                   run_type.replace(" ", "")))
    write_sample_sheet(output_fp, instrument_type, run_id, run['name'],
                       assay, fwd_cycles, rev_cycles, pi_name, pi_email,
                       contact_0_name, contact_0_email, run_type,
                       sample_information)

    studies = []
    for targeted_pool in db.read_pool(pool_id)['targeted_pools']:
        targeted_plate = db.read_targeted_plate(
            targeted_pool['targeted_plate_id'])
        dna_plate = db.read_dna_plate(targeted_plate['dna_plate_id'])
        sample_plate = db.read_sample_plate(dna_plate['sample_plate_id'])
        studies.extend(sample_plate['studies'])

    jira_links = []
    for study_id in set(studies):
        study = db.read_study(study_id)
        issue_key = '%s-4' % study['jira_id']
        jira_handler.add_comment(
            issue_key, "Pools have been sent for sequencing")
        # Add the SampleSheet to the Jira issue
        with open(output_fp, 'rb') as f:
            jira_handler.add_attachment(issue_key, f)
        # Retrieve the jira links so thy can be returned to the user
        project_name = jira_handler.project(study['jira_id']).name
        issue_link = jira_handler.issue(issue_key).permalink()
        jira_links.append([project_name, issue_link])

    return run_id, jira_links


def _copy_sequence_files_to_qiita(prep, run_path):
    """
    Parameters
    ----------
    prep : pandas.DataFrame
        The prep information
    run_path : str
        Path to the directory with the sequencing files

    Returns
    -------
    str, list of (str, str)
        The artifact type and a list of filepaths with
        their Qiita filepath type
    """
    full_fps = []
    path_builder = partial(join, run_path)
    study_id = str(prep.study_id.iloc[0])
    # The structure of the files is different depending on whether the
    # run is of shotgun / target gene and on Hiseq/MiSeq
    if 'target_gene' in prep:
        # Target gene prep. The output is a non-demultiplexed FASTQ
        atype = 'FASTQ'
        # The files are named with the run_name
        run_name = prep.run_name.iloc[0]
        # Start with the forward reads
        full_fps.extend(
            [(fp, 'raw_forward_seqs')
             for fp in glob(path_builder('%s_*_R1_*.fastq.gz' % run_name))])
        # Add the reverse reads
        full_fps.extend(
            [(fp, 'raw_reverse_seqs')
             for fp in glob(path_builder('%s_*_R2_*.fastq.gz' % run_name))])
        # Add the index reads
        full_fps.extend(
            [(fp, 'raw_barcodes')
             for fp in glob(path_builder('%s_*_I1_*.fastq.gz' % run_name))])
    else:
        # Shotgun prep. The output is per sample fastq
        atype = 'per_sample_FASTQ'
        # The samples are prefixed with the study id - take advantage of that
        # Start with the forward reads
        full_fps.extend(
            [(fp, 'raw_forward_seqs')
             for fp in glob(path_builder('%s_*_R1_*.fastq.gz' % study_id))])
        # Add the reverse reads
        full_fps.extend(
            [(fp, 'raw_reverse_seqs')
             for fp in glob(path_builder('%s_*_R2_*.fastq.gz' % study_id))])

    qiita_study_path = join(config.qiita_uploads_dir, study_id)

    filepaths = []
    for full_fp, fp_type in full_fps:
        file_name = basename(full_fp)
        copy(full_fp, qiita_study_path)
        filepaths.append((file_name, fp_type))

    return atype, filepaths


def complete_sequencing_run(success, run_id, run_path, logs):
    """Updates the Jira project and attaches the sequencing data to run_path

    Parameters
    ----------
    success : bool
        Whether the run was successful
    run_id : int
        The run id
    run_path : str
        Path to the directory with the sequencing files
    logs : list of str
        The list of log paths
    """
    run = db.read_sequencing_run(run_id)

    # Retrieve the prep template information from the DB)
    preps = db.generate_prep_information(run_id)
    studies = [prep.study_id.iloc[0] for prep in preps]

    failures = defaultdict(list)
    if success:
        jira_comment = "Sequencing complete. Path to raw files: %s" % run_path
        # Push the prep information to Qiita
        for prep in preps:
            # All the rows have the same value, so I just need to access
            # to a random row to get the study_id -> 0 is guaranteed to exist
            study_id = prep.study_id.iloc[0]

            # Copy the sequencing files to relevant Qiita folders
            atype, filepaths = _copy_sequence_files_to_qiita(prep, run_path)

            dtype = (prep.target_gene.iloc[0]
                     if 'target_gene' in prep else 'Metagenomics')

            prep, _ = _assess_replicates(prep)
            prep['created_on'] = prep.created_on.apply(lambda x: x.isoformat())
            # Cast everything to string: some types generate issues
            prep = prep.astype(str)

            sc, response = qiita_client.post(
                '/api/v1/study/%s/preparation?data_type=%s'
                % (study_id, dtype), data=prep.T.to_dict(), as_json=True)
            if sc != 201:
                msg = response['message'] if response else 'No error specified'
                failures[study_id].append(
                    "[CRITICAL]: FAILURE: Creating Prep Information in study "
                    "%s failed: (%s) %s" % (study_id, sc, msg))
                continue

            # At this point the prep information has been created and the
            # sequencing files are there. Attach the files to the prep
            prep_id = response['id']
            payload = {'artifact_type': atype,
                       'filepaths': filepaths,
                       'artifact_name': run['name']}
            sc, response = qiita_client.post(
                '/api/v1/study/%s/preparation/%s/artifact'
                % (study_id, prep_id), data=payload, as_json=True)
            if sc != 201:
                msg = response['message'] if response else "No error specified"
                failures[study_id].append(
                    "[CRITICAL]: FAILURE: Attaching files to prep information "
                    "%s of study %s failed: (%s) %s"
                    % (prep_id, study_id, sc, msg))
    else:
        jira_comment = (
            "[CRITICAL]: FAILURE: Sequencing run %s (ID: %s). Logs:\n - %s"
            % (run['name'], run['id'], '\n - '.join(logs)))

    # Update the status in Jira independently of run status
    for study_id in set(studies):
        study = db.read_study(study_id)
        issue_key = '%s-5' % study['jira_id']
        jira_handler.add_comment(issue_key, jira_comment)

        error_comment = failures[study_id]
        if error_comment:
            jira_handler.add_comment(issue_key, '\n'.join(error_comment))


# 1 - Project initiation
ISSUE1_DESC = """
When this step is complete, we will have:

- the general concept of the project
- the name and contact of the lead person
- names and contacts of internal and external collaborators who will form the\
 team
- funding sources with indexes where applicable
"""


# 2 - Experimental design
ISSUE2_DESC = """
When this task is complete there will be a Powerpoint or PDF that clearly \
describes:

- The goal of project
- The experimental design
- The number of samples
- The number of subjects
- The variables that will be analyzed (technical and biological)
- Potential pitfalls
- A plan for how the analysis will be done
"""


# 3 - Sample receipt
ISSUE3_DESC = """
When this task is complete we will have:

- inventory of the samples (number and kind)
- location of where the samples are
- information about whether and how the samples can be re-used
- contact information (name and email) for the specific people involved in\
 gathering, labeling and shipping the samples
- sample manifest that is labeled exactly the same way the samples are
- if appropriate, an MTA allowing us to actually use the samples and/or\
 resulting data
"""


# 4 - Library preparation
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
- metabolomics
"""


# 5 - Molecular characterization and data transfer
ISSUE5_DESC = """
When this task is complete, the data will have been generated on the \
appropriate instrument, and transferred to the correct file stores and \
uploaded to qiita and/or gnps as appropriate
"""


# 6 - Data analysis
ISSUE6_DESC = """
When this step is complete, the data will have been analyzed and the \
following will be available:

- Internal accession numbers in qiita and/or gnps
- Figures and tables showing the results of the analysis
- Summary of the main results of the project
"""


# 7 - Manuscript preparation and submission
ISSUE7_DESC = """
When this task is complete:

- External accession numbers (e.g. ebi or massive) will have been obtained
- Manuscript will be completely written and approved by all authors
- Manuscript will have been submitted to a journal
- Confirmation of receipt from the journal will have been logged
"""
