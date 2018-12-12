# The Makefile is partly for usability and partly for documenting processes.

check: lint test

clean:
	rm tags
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +

cloc:
	cloc lib *.py static resources test views

css: resources/scss/*.scss
	pyscss -o static/main.css resources/scss/main.scss

lint:
	flake8

push: clean test
	# Unnecessary, retainedas example
	# aws s3 sync static/ s3://static.chapman.wiki/

run: test
	python app.py

redis:
	docker run \
		--name aw-redis \
		-v /docker/article-wiki-redis:/data \
		-p 6379:6379 \
		-d redis \
		redis-server --appendonly yes

tags:
	tags -R --exclude .venv

test:
	pytest lib
	pytest test

uwsgi: 
	uwsgi uwsgi.ini
