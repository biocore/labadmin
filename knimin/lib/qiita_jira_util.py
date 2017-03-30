#!/usr/bin/env python
from knimin import jira_handler
from jira import JIRAError


def create_project(project_name, assignee=None,
                   template_name="Project Management"):
    """Returns an open JIRA connection handler

    Parameters
    ----------
    project_name : str
        The project name
    assignee : str, optional
        Username of the person assigned to this project
    template_name : str, optional
        The template name

    Returns
    -------
    jira.resources.Project
        The recently created JIRA project
    str
        Error message if failure
    """
    # study_id will be provided by Qiita, hardcoding it
    study_id = 10001
    message = ''
    key = '%sKK%d' % (
        ''.join([k[0] for k in template_name.split(' ') if k]).upper(),
        study_id)

    print key, template_name
    try:
        jira_project = jira_handler.create_project(
            key=key, name=project_name, assignee=assignee,
            template_name=template_name)
    except JIRAError as e:
        jira_project = None
        message = e.text

    return jira_project, message
