Knight Lab administrative portal
================================

This is the internal Knight Lab administration portal for creating, tracking, and processing general barcodes and the American Gut.


Installation instructions
-------------------------

Create a conda environment for labadmin::

   conda create -n labadmin psycopg2 python=2 click requests bioconda java-jdk

   source activate labadmin

Clone the repository, and pip install::

   git clone https://github.com/biocore/labadmin.git

   cd labadmin
   pip install -e .

Copy the example config file to be visible for starting up a test database::

   cp ./knimin/config.txt.example ./knimin/config.txt

**Installing JIRA**

Note that these instructions should work for Mac or Linux and that you need to have JAVA 1.8 or higher which
is already installed in the conda command. However, if are not using conda you can simply download the
`latests JAVA version <http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html>`__ and add it
to your environment by::

    export JAVA_HOME='/Library/Java/JavaVirtualMachines/jdk1.8.0_121.jdk/Contents/Home'

Now you can continue with downloading the latest `JIRA SDK <https://marketplace.atlassian.com/download/plugins/atlassian-plugin-sdk-tgz>`__,
uncompressing it and setting it up::

    curl -o atlassian-plugin-sdk-6.2.14.tar.gz https://marketplace.atlassian.com/download/plugins/atlassian-plugin-sdk-tgz
    tar zxvf atlassian-plugin-sdk-6.2.14.tar.gz
    mv atlassian-plugin-sdk-6.2.14 atlassian-plugin-sdk
    export PATH="$PATH:${PWD}/atlassian-plugin-sdk/bin"

To test the install you can run::

    atlas-version

and to start the JIRA system locally::

    # </dev/zero 2>&1 & --> https://goo.gl/n7BYnh
    atlas-run-standalone --product jira </dev/zero 2>&1 &

Now, you should now be able to start the webserver::

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

After executing our existing unit test suite, access level for the user 'test' will be reset to '', i.e. they won't be able to see most of the main menu items. Thus, adding a second user 'master' with admin privileges is quite useful.
