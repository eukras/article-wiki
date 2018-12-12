# Installation

For a production installation, see DEPLOY.md.

Tested on Python 3.5, Redis 5.0, and Ubuntu. Standard Virtualenv is the only 
system requirement. 

```bash
cd root_dir  # <-- whereever this INSTALL file is.
virtualenv --python=python3 .venv
source .venv/bin/activate
python --version  # <-- should see e.g. 3.5+
pip --version  # <-- should see (Python e.g. 3.5+)
pip install -r requirements.txt -r requirements-dev.txt
pip freeze  # <-- show dependencies
pytest lib/  # <-- unit tests
pytest test/  # <-- web tests
```

You'll need a Redis server; customise localhost:6379 in .env if needed. To run
one in Docker with persistent storage, use the Makefile: 

```bash
make redis
```

Run the app for dev purposes. Note that this is not an efficient way to run the
app online; suggest Nginx, uWsgi, and Supervisor.

```bash
vim .env  # <-- Defaults to localhost:8080
set -a && source .env && set +a
python command.py load-fixtures  # <-- Load initial docs.
python app.py
```

And view http://localhost:8080.

# Running in NGINX and UWSGI

The supplied uwsgi.ini file will operate nicely with the supplied nginx.conf.
This uses a TCP port, and UWSGI is told to grab the bottleApp from app.py.

```bash
sudo apt-get install build-essentials python3-dev
pip install uwsgi
uwsgi uwsgi.ini
```

Then start NGINX:

Set correct server name in install/etc/nginx/sites-enabled/default, add HTTPS
if required, then:

```bash
vim install/etc/nginx/sites-enabled/default  # <-- set server_name, etc
sudo apt-get install nginx
sudo cp install/etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default
sudo service nginx restart
```

This will serve the static/ dir from nginx rather than through the Python app,
and add some micro-caching.

And view http://localhost (or as specified).

# Add Supervisor (or systemd)

Note this will require ENV.dist to be effectively provided in the conf.

```bash
[program:...]
environment = 
    SITE=domain1,
    DJANGO_SETTINGS_MODULE=foo.settings.local,
    DB_USER=foo,
    DB_PASS=bar
command = ...
```
