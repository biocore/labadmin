Knight Lab administrative portal
================================

This is the internal Knight Lab administration portal for creating, tracking, and processing general barcodes and the American Gut.


Installation instructions
-------------------------

Create a conda environment for labadmin::

   conda create -n labadmin psycopg2 python=2 click requests

   source activate labadmin

Clone the repository, and pip install::

   git clone https://github.com/biocore/labadmin.git

   cd labadmin
   pip install -e .

Copy the example config file to be visible for starting up a test database::
   
   cp ./knimin/config.txt.example ./knimin/config.txt

You should now be able to start the webserver::

   python ./knimin/webserver.py

And log on to the test database at localhost:7777, or whichever port you specified in config.txt.

Initial default test login credentials are:

**User:** test

**Password:** password 

Testing
-------

To run the webserver locally, first run the following commands to insert a user with administrative access::

    \c ag_test

    INSERT INTO ag.labadmin_users (email, password) VALUES ('master', '$2a$10$2.6Y9HmBqUFmSvKCjWmBte70WF.zd3h4VqbhLMQK1xP67Aj3rei86');
    
    INSERT INTO ag.labadmin_users_access (access_id, email) VALUES (7, 'master');
    
Then you should be able to login with the following credentials

**User:** master

**Password:** password 

Note that whenever a unittest is run, the user `test` is granted admin rights, which is reset once the unittest is completed.
