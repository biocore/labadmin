# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from knimin import jira_handler, qiita_client, db


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
