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

The code in this repository assumes a Python 3 environment. You can use either 
`conda` or `pip` as described below.

#### Dependencies via `conda`

You can replicate the environment used to run the C-GEM Portal by using conda
to install the virtual environment specified by the supplied environment files.

- `environment.lock.yaml` specifies all precise version numbers.
- `environment.abstract.yaml` specifies packages without version numbers.

With a Conda distribution installed, you can create a virtual environment as
follows:

```bash
conda env create -n portal -f environment.lock.yaml
```

Activate the environment using `conda activate portal`.

#### Dependencies via `pip`

As an alternative to conda, you can use pip to install dependencies, using:
```bash
pip install -r requirements.txt
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
- The Flask environment (development, testing, or production) and port 
- G Suite credentials data
- the Team Drive alphanumeric ID
- the directory ID for the Compounds protocols folder within the Team Drive
- a path to save a local copy of the protocols listing ('compounds.pickle')
- development and production database details for the Strains app
- Asana workspace info and credentials

`.env_demo`:
```bash
PY_HOME=/path/to/python/environment/dir
FLASK_ENV=production
FLASK_RUN_PORT=5100
GOOGLE_CLIENT_ID=xxxx-yyyy.apps.googleusercontent.com
GOOGLE_SECRET=zzzz
SERVICE_ACCOUNT_FILE=/path/to/service-account-key.json
CREDENTIALS_AS_USER=admin@example.com
GROUP_KEY=fakegroupkey
TEAM_DRIVE_ID=xxxxxxxxxxxxxxxxx
CALENDAR_ID=example.com_12345abc1234@group.calendar.google.com
COMPOUNDS_DIR_ID=yyyyyyyyyyy
COMPOUNDS_PICKLE=compounds.pickle
DATABASE_URL_DEV=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains_dev
DATABASE_URL=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains
DB_NAME_DEV=strains_dev
DB_NAME=strains
DB_HOST=localhost
SQLALCHEMY_ECHO=False
ASANA_TOKEN=0/123456789abcdef
ASANA_WORKSPACE_ID=1234567890
ASANA_TEAM_ID=0987654321
```

Note that there are four rows corresponding to Google credentials data. 
`GOOGLE_CLIENT_ID` and `GOOGLE_SECRET` are for an OAuth client ID, used during 
the login process. `SERVICE_ACCOUNT_FILE` is used to specify a JSON credentials
file corresponding to a service account with domain-wide delegation, and
`CREDENTIALS_AS_USER` specifies a corresponding user with privileges to mimic. 


### Running the app

The app can be served by running either the `start_portal.sh` script or, when 
the python environment is activated, by executing the command `flask run`. In 
both cases the `flask` executable serves the app on the port specified in your
.env file. With the port set as e.g. 5100, the app will then be accessible
from your browser at `http://localhost:5100`.
