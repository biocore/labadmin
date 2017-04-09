# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The LabAdmin Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from knimin import jira_handler, qiita_client, db


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
    # Generate the Jira key
    key = '%s%d' % (
        ''.join([k[0] for k in jira_template.split(' ') if k]).upper(),
        study_id)
    jira_project = jira_handler.create_project(
        key=key, name=title, assignee=jira_user,
        template_name=jira_template)

    # Step 3: Create the study locally
    db.create_study(study_id, title, alias, jira_project['projectKey'])

    return study_id
