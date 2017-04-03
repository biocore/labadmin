#!/usr/bin/env python
from jira import JIRA


def create_jira_handler(config):
    """Returns an open JIRA connection handler

    Parameters
    ----------
    config : config object
        The config object with the jira configuration
    """
    if not config.jira_passkey:
        return JIRA(options={
            'server': config.jira_host},
            basic_auth=(config.jira_user, config.jira_password))
    else:
        raise ValueError("passkey connection to JIRA not implemented")
