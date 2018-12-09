check: lint test

clean:
	rm tags
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +

cloc:
	cloc lib *.py static resources test views

css: resources/scss/*.scss
	pyscss -o static/main.css resources/scss/main.scss

env: 
	set -a && source .env && set +a

lint:
	flake8

push: clean test
	# aws s3 sync static/ s3://static.article-wiki.wiki/

run: test
	python app.py

redis:
	sudo docker run \
		--name article-wiki-redis \
		-v /docker/article-wiki-redis:/data \
		-p 6379:6379 \
		-d redis \
		redis-server --appendonly yes

tags:
	tags -R --exclude .venv

test:
	pytest
