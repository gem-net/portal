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

The code in this repository assumes a Python 3 environment. Python dependencies 
are specified in a `requirements.txt` files. Install with `pip` using:
```
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
- G Suite credentials data
- development and production database details for the Strains app
- the Team Drive alphanumeric ID
- the directory ID for the Compounds protocols folder within the Team Drive
- a path to save a local copy of the protocols listing ('compounds.pickle')

`.env_demo`:
```bash
GOOGLE_CLIENT_ID=xxxx-yyyy.apps.googleusercontent.com
GOOGLE_SECRET=zzzz
APP_URL=http://localhost:5101/bk_server
DATABASE_URL_DEV=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains_dev
DATABASE_URL=mysql+pymysql://fakeuser:fakepassword@127.0.0.1:3306/strains
DB_NAME_DEV=strains_dev
DB_NAME=strains
DB_CNF=/path/to/.my.cnf
DB_HOST=localhost
SQLALCHEMY_ECHO=False
SERVICE_ACCOUNT_FILE=/path/to/service-account.json
GROUP_KEY=fakegroupkey
CREDS_JSON=/path/to/credentials.json
TEAM_DRIVE_ID=xxxxxxxxxxxxxxxxx
COMPOUNDS_DIR_ID=yyyyyyyyyyy
COMPOUNDS_PICKLE=compounds.pickle
```


### Running the app

The Flask app can be served with the command below. This command sets two 
environment variables: the path to `app.py`, and server mode 
(`production` or `development`).

```bash
FLASK_APP=/path/to/portal/app.py FLASK_ENV=production flask run --port 5110
``` 

The command above serves the app on port 5110. It should now be accessible 
from your browser at `http://localhost:5110`.