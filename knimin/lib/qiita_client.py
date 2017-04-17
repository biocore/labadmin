# This code is based on the QiitaClient project
# https://github.com/qiita-spots/qiita_client
# We can't directly use the QiitaClient library because it doesn't play nice
# with the new restAPI due to the returning status codes.
# Hence, including here the copyright notice from the QiitaClient project

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from json import dumps

import requests


class QiitaClient(object):
    """Client of the Qiita RESTapi

    Parameters
    ----------
    server_url : str
        The url of the Qiita server
    client_id : str
        The client id to conenct to the Qiita server
    client_secret : str
        The client secret id to connect to the Qiita server
    server_cert : str, optional
        The server certificate, in case that it is not verified


    Methods
    -------
    get
    post
    """
    def __init__(self, server_url, client_id, client_secret, server_cert=None):
        self._server_url = server_url

        # The attribute self._verify is used to provide the parameter `verify`
        # to the get/post requests. According to their documentation (link:
        # https://goo.gl/ZNsmk2 ) verify can be a boolean indicating
        # if certificate verification should be performed or not, or a
        # string with the path to the certificate file that needs to be used
        # to verify the identity of the server.
        # We are setting this attribute at __init__ time so we can avoid
        # executing this if statement for each request issued.
        if not server_cert:
            # The server certificate is not provided, use standard certificate
            # verification methods
            self._verify = True
        else:
            # The server certificate is provided, use it to verify the identity
            # of the server
            self._verify = server_cert

        # Set up oauth2
        self._client_id = client_id
        self._client_secret = client_secret
        self._authenticate_url = "%s/qiita_db/authenticate/" % self._server_url

        self._session = requests.Session()

        # Fetch the access token
        self._fetch_token()

    def _fetch_token(self):
        """Retrieves an access token from the Qiita server

        Raises
        ------
        ValueError
            If the authentication with the Qiita server fails
        """
        data = {'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client'}
        r = self._session.post(self._authenticate_url, verify=self._verify,
                               data=data)
        if r.status_code != 200:
            raise ValueError("Can't authenticate with the Qiita server")
        self._token = r.json()['access_token']

    def _request_oauth2(self, req, url, as_json=False, **kwargs):
        """Executes a request using OAuth2 authorization

        Parameters
        ----------
        req : function
            The request to execute
        url : str
            The url to access in the server
        as_json : bool, optional
            If true, encode the request data using JSON
        kwargs : dict
            The request kwargs

        Returns
        -------
        requests.Response
            The request response
        """
        url = self._server_url + url

        if 'headers' in kwargs:
            kwargs['headers']['Authorization'] = 'Bearer %s' % self._token
        else:
            kwargs['headers'] = {'Authorization': 'Bearer %s' % self._token}

        if 'data' in kwargs and as_json:
            kwargs['data'] = dumps(kwargs['data'])

        r = req(url, verify=self._verify, **kwargs)
        r.close()

        try:
            r_json = r.json()
        except Exception:
            r_json = None

        if r.status_code == 400:
            if r_json and r_json.get('error_description') == \
                    'Oauth2 error: token has timed out':
                # The token expired - get a new one and re-try the request
                self._fetch_token()
                kwargs['headers']['Authorization'] = 'Bearer %s' % self._token
                r = req(url, verify=self._verify, **kwargs)

        return r.status_code, r_json

    def get(self, url, **kwargs):
        """Execute a get request against the Qiita server

        Parameters
        ----------
        url : str
            The url to access in the server
        kwargs : dict
            The request kwargs

        Returns
        -------
        int, dict
            The status code and the JSON response from the server
        """
        return self._request_oauth2(self._session.get, url, **kwargs)

    def post(self, url, **kwargs):
        """Execute a post request against the Qiita server

        Parameters
        ----------
        url : str
            The url to access in the server
        kwargs : dict
            The request kwargs

        Returns
        -------
        int, dict
            The status code and the JSON response from the server
        """
        return self._request_oauth2(self._session.post, url, **kwargs)

    def patch(self, url, **kwargs):
        """Executes a patch request against the Qiita server

        Parameters
        ----------
        url : str
            The url to access in the server
        kwargs : dict
            The request kwargs

        Returns
        -------
        int, dict
            The status code and the JSON response from the server
        """
        return self._request_oauth2(self._session.patch, url, **kwargs)
