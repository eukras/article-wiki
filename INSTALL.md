# Installation

## Basic Development System

Tested on Python 3.11 and Redis 7.2.

```bash
sudo apt-get install virtualenv
cd root_dir  # <-- whereever this INSTALL.md file is.
virtualenv --python=python3 .venv
source .venv/bin/activate
python --version  # <-- should see e.g. 3.10+
pip --version  # <-- should see (Python e.g. 3.10+)
pip install -r requirements.txt -r requirements-dev.txt
pip freeze  # <-- show dependencies
pytest lib/  # <-- unit tests
pytest test/  # <-- web tests
```

Note that changes to `src/` and `resources/scss` will need to be rebuilt with
`npm run build`. This creates `dist/bundle.js` (with Rollup) and
`static/main.css` (with SASS).

FastAPI provides a generated set of API docs at `/docs`.


## Database

You'll need a Redis server; customise the `localhost:6379` port in `ENV.dist`
if needed. To run one in Docker with persistent storage, use the Makefile: 

```bash
make redis
```

To run the app for dev purposes:

```bash
vim ENV.dist  # <-- Configure; defaults to localhost:8000
set -a && source ENV.dist && set +a  # <-- Export all environment vars
python command.py initialize  # <-- Create admin user, load initial docs
uvicorn main:app --reload  # <-- run, and reload to pickup changes
```

Then view `http://localhost:8000`, and sign in with $ADMIN_USER and $ADMIN_PASSWORD 
from ENV.dist (or as otherwise set in ENV vars).

## Testing

To verify that things are working: 

```
pytest
pytest -m integration   # <-- If there's a redis connection available
                        #     with a disposable test database.
```

## Production

This is a FastAPI app, for which there are many deployment solutions.  

The `install/docker` directory copntains a `Dockerfile` that can be used to build a 
Linux container from python-slim.
