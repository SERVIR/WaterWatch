Web Application
======================================

**This app is created to run in the Teyths Platform programming environment.** 

**You can find a working demo here at** |http://tethys.servirglobal.net/apps/waterwatch/|

.. |http://tethys.servirglobal.net/apps/waterwatch/| raw:: html


    <a href="http://tethys.servirglobal.net/apps/waterwatch/" target="_blank">http://tethys.servirglobal.net/apps/waterwatch/ </a>

.. note::

    The following instructions have been tested on Ubuntu 16.04. Your workflow might be slightly different based on the operating system that you are using.


Prerequisites
----------------

- Tethys Platform (CKAN, PostgresQL, GeoServer
- Google Earth Engine Python API
- Google Earth Engine Service Account (For Production, not needed for development)

Install Tethys Platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~
See: |http://docs.tethysplatform.org/en/latest/installation.html|

.. |http://docs.tethysplatform.org/en/latest/installation.html| raw:: html


    <a href="http://docs.tethysplatform.org/en/latest/installation.html" target="_blank">http://docs.tethysplatform.org/en/latest/installation.html </a>



Install the Google Earth Engine Python API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before installing the API you need to sign up for access to the Google Earth Engine API |https://signup.earthengine.google.com/#!/|.

.. |https://signup.earthengine.google.com/#!/| raw:: html


    <a href="https://signup.earthengine.google.com/#!/" target="_blank">here</a>

Activate your Tethys conda environment using the alias `t`:

::

    $ t

Install the Google APIs Client Library

::

    (tethys)$ sudo pip install google-api-python-client


Install the Earth Engine Python API

::

    (tethys)$ sudo pip install earthengine-api

Authenticate your machine

::

    (tethys)$ earthengine authenticate


Follow the instructions as presented on the screen. Open a new webpage and paste the link as presented on the screen. If you are not already signed in with your Google Account, you will be prompted to do so at this time. Once authenticated, the web page will ask you to authorize access to Earth Engine data. Click accept, and the web page will present you with an authorization code. Copy the authorization code, and paste it in the terminal where the authenticate process is running. The script will write credentials file to the correct location on your file system

Enter the following command in the terminal to confirm if Earth Engine API has been installed properly. If there is no message it means that your machine is authenticated to access the Earthe Engine API. 

::

    (tethys)$ python -c "import ee; ee.Initialize()"

.. warning::

    The steps for authenticating are slightly different for production installation. The steps for authenticating the app in production instance are provided later on this page.


Web App Installation
----------------------

Installation for App Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Download the source code from github. (Activate the tethys environment if it isn't already activated.)

::

    $ t
    (tethys)$ git clone https://github.com/SERVIR/WaterWatch
    (tethys)$ cd WaterWatch
    (tethys)$ python setup.py develop

Start the Tethys Server

::

    (tethys)$ tms


You should now have the WaterWatch (Ferlo Ephemeral Water Body Monitoring Dashboard) app running on a development server on your machine. Tethys Platform provides a web interface called the Tethys Portal. You can access the app through the Tethys portal by opening http://localhost:8000/ (or if you provided custom host and port options to the install script then it will be <HOST>:<PORT>) in a new tab in your web browser.

Installation for Production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Installing apps in a Tethys Platform configured for production can be challenging. Most of the difficulties arise, because Tethys is served by Nginx in production and all the files need to be owned by the Nginx user. The following instructions will allow you to deploy the WaterWatch app on to your own Tethys production server. You can find the Tethys Production installation instructions `here. <http://docs.tethysplatform.org/en/stable/installation/production.html>`_


Change the Ownership of the Files to the Current User


*During the production installation any Tethys related files were change to be owned by the Nginx user. To make any changes on the server it is easiest to change the ownership back to the current user. This is easily done with an alias that was created in the tethys environment during the production installation process*


::

    $ t
    (tethys)$ tethys_user_own

Download App Source Code from GitHub

::

    $ cd $TETHYS_HOME/apps/
    $ sudo git clone https://github.com/SERVIR/WaterWatch

.. tip::

    Substitute $TETHYS_HOME with the path to the tethys main directory.

Here comes the tricky part! You will need to create a Google Cloud Platform Account (|https://cloud.google.com/|). Once you have signed up for it you can create a service account and a private key for the app instace on the google cloud. Then request the Google Earth Engine team to white-list your service account. 


.. |https://cloud.google.com/| raw:: html


    <a href="https://cloud.google.com/" target="_blank">https://cloud.google.com/ </a>

Once you have the service account email and private key. Change the :file:`utilities.py` file accordingly.

Place the private key on the production machine in a location of your choice.

Open the :file:`utilities.py` for editing using ``vim`` or any text editor of your choice:

::

    (tethys)$ cd $TETHYS_HOME/apps/WaterWatch/tethysapp/waterwatch
    (tethys)$ sudo vi utilities.py


Press :kbd:`i` to start editing and enter service account email and private key filename. You can find it right after the import statements. 

This how the statement looks before changing it. Currently the service account email and filename are empty strings. Change them to your Google Cloud Service Account Email and to the location of the private key on your production instance.


::

    try:
        ee.Initialize()
    except EEException as e:
        from oauth2client.service_account import ServiceAccountCredentials
        credentials = ServiceAccountCredentials.from_p12_keyfile(
        service_account_email='',
        filename='',
        private_key_password='notasecret',
        scopes=ee.oauth.SCOPE + ' https://www.googleapis.com/auth/drive ')
        ee.Initialize(credentials)


This is how it could look like when you are done.

::

    try:
        ee.Initialize()
    except EEException as e:
        from oauth2client.service_account import ServiceAccountCredentials
        credentials = ServiceAccountCredentials.from_p12_keyfile(
        service_account_email='myserviceaccount.gi@google.com',
        filename='/home/productionmachine/private_key.pem',
        private_key_password='notasecret',
        scopes=ee.oauth.SCOPE + ' https://www.googleapis.com/auth/drive ')
        ee.Initialize(credentials)

.. Note::

    Except for the service_account_email and filename you do not have to change anything else. You can leave the other parameters as is.

.. Warning::

    If you fail to do the above step it will break your Tethys portal. Be sure to look out for types...tipos..typos.....

Press :kbd:`ESC` to exit ``INSERT`` mode and then press ``:x`` and :kbd:`ENTER` to save changes and exit.


Return to the main directory of the app. Then, execute the setup script (:file:`setup.py`) with the ``install`` command to make Python aware of the app and install any of its dependencies

::

    (tethys)$ cd $TETHYS_HOME/apps/WaterWatch/
    (tethys)$ python setup.py install


Collect Static Files and Workspaces

The static files and files in app workspaces are hosted by Nginx, which necessitates collecting all of the static files to a single directory and all workspaces to another single directory. These directory is configured through the ``STATIC_ROOT`` and ``TETHYS_WORKSPACES_ROOT`` setting in the :file:`settings.py` file. Collect the static files and workspaces with this command

::

    (tethys)$ tethys manage collectall

Change the Ownership of Files to the Nginx User

The Nginx user must own any files that Nginx is serving. This includes the source files, static files, and any workspaces that your app may have. The following alias will accomplish the change in ownership that is required

::

    (tethys)$ tethys_server_own
     

Restart uWSGI and Nginx services to effect the changes

::

    $ sudo systemctl restart tethys.uwsgi.service
    $ sudo systemctl restart nginx

.. note::

    For updating the app on production server, simply pull the app from GitHub. Once you have made a pull request (at times you may have to stash your local changes), follow the above steps to reinstall/update the app. You will have reenter the service account name and filename in the :file:`utilities.py` file.



































































    


