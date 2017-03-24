#!/usr/bin/env python
from jira import JIRA


def jira_connect(server='https://jira.atlassian.com',
                 user=None, password=None):
    """Connect to JIRA server

    Parameters
    ----------
    server: str, optional
        the servername to connect
    user: str, optional
        the user to connect as
    password: str, optional
        the password of the user

    Raises
    ------
    ValueError, if the user or password are None but the other is not
    """
    if user is not None or password is not None:
        if user is None or password is None:
            raise ValueError('password and user should be both None or both '
                             'have a value')

        jira = JIRA(options={'server': server}, basic_auth=(user, password))
    else:
        jira = JIRA(options={'server': server})

    return jira


def get_projects():
    """Connect to JIRA server

    Returns
    -------
    list of available projects
    """
    jira = jira_connect()
    return jira.projects()
