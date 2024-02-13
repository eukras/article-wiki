# The Makefile is partly for usability and partly for documenting processes.

check: lint test

clean:
	rm tags
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +

cloc:
	cloc lib *.py static resources test views

pyscss: resources/scss/*.scss
	pyscss -o static/main.css resources/scss/main.scss
	pyscss -o static/epub.css resources/scss/epub.scss

css:
	sass resources/scss/main.scss static/main.css
	sass resources/scss/epub.scss static/epub.css

csswatch:
	sass --watch resources/scss/main.scss static/main.css


lint:
	flake8

run: test
	python app.py

redis:
	docker run \
		--name aw-redis \
		--network host \
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
