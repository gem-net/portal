GEM-NET Members Portal
======================

A user portal to gather useful info, data, and analytics for team members.

![Homepage](portal_homepage.png)

The homepage of this app features:
- a list of upcoming events from the team Google Calendar
- counts of shipment requests by status, from the Strains app
- a list of the most recently modified documents from the Team Drive.
- links to external resources, including the team website, the Strains app, 
 Slack, Benchling, and Asana.


## Setup instructions

### Python package dependencies

The code in this repository assumes a Python 3 environment. 

You can replicate the environment used to run the C-GEM Portal by using conda
to install the virtual environment specified by the supplied environment files.

- `environment.lock.yaml` specifies all precise version numbers.
- `environment.abstract.yaml` specifies packages without version numbers.

With a Conda distribution installed, you can create a virtual environment as
follows:

```bash
conda env create -n portal -f environment.lock.yaml
```

### Other requirements

- This app assumes that the `Strains app` (https://github.com/gem-net/strains) 
is already set up and running. 


### env files

The env files specifies configuration detail that is not suitable for hard-coding. 
A demo env files, `.env_demo` has been provided, which you should 
update and rename to `.env`. 

The env file is used to specify:
- The path to the app-specific python environment (includes bin and lib subdirectories).
- The environment for Flask: development, testing, or production 
- G Suite credentials data
- development and production database details for the Strains app
- the Team Drive alphanumeric ID
- the directory ID for the Compounds protocols folder within the Team Drive
- a path to save a local copy of the protocols listing ('compounds.pickle')

`.env_demo`:
```bash
PY_HOME=/path/to/python/environment/dir
FLASK_ENV=production
GOOGLE_CLIENT_ID=xxxx-yyyy.apps.googleusercontent.com
GOOGLE_SECRET=zzzz
DATABASE_URL_DEV=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains_dev
DATABASE_URL=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains
DB_NAME_DEV=strains_dev
DB_NAME=strains
DB_HOST=localhost
SQLALCHEMY_ECHO=False
SERVICE_ACCOUNT_FILE=/path/to/service-account.json
GROUP_KEY=fakegroupkey
CREDS_JSON=/path/to/credentials.json
TEAM_DRIVE_ID=xxxxxxxxxxxxxxxxx
COMPOUNDS_PICKLE=compounds.pickle
COMPOUNDS_DIR_ID=yyyyyyyyyyy
```


### Running the app

The app can be served by running the `start_portal.sh` script. It uses 
the `flask` executable to serve the app on the port specified in your
.env file (or port 5110 if not provided). If you use the default port, the app 
will be accessible from your browser at `http://localhost:5110`.
