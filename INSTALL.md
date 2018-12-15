# Installation

## Basic Development System

Tested on Python 3.5, Redis 5.0, and Ubuntu. The code can be obtained by Git or
as a `.zip` download. Redis can be installed locally or run in Docker.
Virtualenv is the only absolute prerequisite.

```bash
sudo apt-get install virtualenv
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

Currently we use a locale hack for currency formatting in tables; until fixed,
AWS/Ubuntu systems will need this hack:

```bash
sudo apt-get install locales
sudo locale-gen en_CA.UTF-8
```

You'll need a Redis server; customise the `localhost:6379` port in `ENV.dist`
if needed. To run one in Docker with persistent storage, use the Makefile: 

```bash
make redis
```

Run the app for dev purposes. Note that this is not an efficient way to run the
app online; suggest Nginx, uWsgi, and Supervisor (see below).

```bash
vim ENV.dist  # <-- Defaults to localhost:8080
set -a && source ENV.dist && set +a
python command.py initialize  # <-- Create admin user, load initial docs.
python app.py
```

And view `http://localhost:8080`.


## Running in NGINX and UWSGI

The supplied `uwsgi.ini` file will operate nicely with the supplied
`install/etc/nginx/sites-enabled/default`. This uses a TCP port, and tells
UWSGI to grab the bottleApp from app.py.

```bash
sudo apt-get install build-essentials python3-dev
pip install uwsgi
uwsgi uwsgi.ini
```

Set correct server name in `install/etc/nginx/sites-enabled/default`, add HTTPS
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

This Nginx default config runs on HTTP, which is terrible practice. Use it just
for the purpose of authenticating your LetsEncrypt certificates. Certbot will
rewrite your config so you end up with something closer to
`install/etc/nginx/sites-enabled/default-ssl`, which you should then use
instead.

```bash
apt-get install certbot python-certbot-nginx
certbot --nginx -d example.com
```

Then restart Nginx again, and check that you domain redirects automatically to
HTTPS from HTTP.


# Future: Add Supervisor (or systemd)

*TODO*

Your UWSGI app needs to start on system load, and after restarts,
crashes, or if you kill the process to force it to reload. That probably means
`supervisor` or `systemd`. Note this will require ENV.dist to be
effectively provided in the supervisor.conf; there's a non-working
sample in `etc/supervisor/...`.

```bash
[program:...]
environment = 
    SITE=domain1,
    DJANGO_SETTINGS_MODULE=foo.settings.local,
    DB_USER=foo,
    DB_PASS=bar
command = ...
```
