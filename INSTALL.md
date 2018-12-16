# Installation

## Basic Development System

Tested on Python 3.5-6, Redis 5.0, and Ubuntu, incl. AWS Ubuntu. The code can
be obtained by Git or as a `.zip` download. Redis can be installed locally or
run in Docker.  Virtualenv is the only absolute prerequisite.

```bash
sudo apt-get install virtualenv
cd root_dir  # <-- whereever this INSTALL.md file is.
virtualenv --python=python3 .venv
source .venv/bin/activate
python --version  # <-- should see e.g. 3.5+
pip --version  # <-- should see (Python e.g. 3.5+)
pip install -r requirements.txt -r requirements-dev.txt
pip freeze  # <-- show dependencies
pytest lib/  # <-- unit tests
pytest test/  # <-- web tests
```

Currently using a locale hack for currency formatting in tables; until fixed,
AWS/Ubuntu systems will need:

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
app online; suggest `nginx`, `uwsgi`, and `systemd` (see below).

```bash
vim ENV.dist  # <-- Defaults to localhost:8080
set -a && source ENV.dist && set +a  # <-- Export all environment vars
python command.py initialize  # <-- Create admin user, load initial docs
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

If running interactively, stop that with `^C`; if otherwise, use:

```bash
which uwsgi  # <-- shows /app/.venv/bin/uwsgi
killall -9 /app/.venv/bin/uwsgi
```

This needs an webserver front end. Set correct server name in
`install/etc/nginx/sites-enabled/default` then:

```bash
vim install/etc/nginx/sites-enabled/default  # <-- set server_name, etc
sudo apt-get install nginx
sudo cp install/etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default
sudo service nginx restart
```

This will serve the `static/` dir from nginx rather than through the Python app,
and add some micro-caching.

You should now be able to view http://localhost (or as specified).

This Nginx default config runs on HTTP, which is insecure. Use it just for the
purpose of authenticating the LetsEncrypt certificates. Certbot will rewrite
your config so you end up with something closer to
`install/etc/nginx/sites-enabled/default-ssl`, which you should then use
instead.

```bash
apt-get install certbot python-certbot-nginx
certbot --nginx -d example.com
```

Then restart Nginx again, and check that your domain redirects automatically
from HTTP to HTTPS.


## Managing Article Wiki with Systemd

Running uWsgi in `master` mode (see `uwsgi.ini`) is reslient to crashes or to
individual threads being killed, but isn't particularly intuitive to control 
and won't survive a system restart. For that we'll need to switch to system 
`uwsgi`, and `systemd`, and also provide ENV variables to systemd with a 
`ENV.vars` file.

```bash
cd $root_dir  # <-- Location of this INSTALL.md file.
cp ENV.dist ENV.vars
vim ENV.vars  # <-- These values will be used by the article-wiki.service
pip uninstall uwsgi
sudo apt-get install uwsgi uwsgi-plugin-python3
which uwsgi  # <-- Make sure this is used in the service definition:
vim install/etc/systemd/system/article-wiki.service
sudo cp install/etc/systemd/system/article-wiki.service /etc/systemd/system/article-wiki.service
sudo systemctl daemon-reload  # <-- To reread the services when they've changed
sudo systemctl enable article-wiki.service
```

Now the app survives rebooting, and you control it with:

```bash
sudo service article-wiki [start|status|restart|stop]

# Or, similarly...
sudo systemctl start article-wiki.service
sudo journalctl -fu article-wiki.service  # <-- Logs
```


## Dockerize Application

... Next!
