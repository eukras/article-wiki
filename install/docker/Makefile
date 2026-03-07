redis:
	docker run \
		--name aw-redis \
		--network host \
		-v /docker/article-wiki-redis:/data \
		-p 6379:6379 \
		-d redis \
		redis-server --appendonly yes

build:
	docker build -t article-wiki:latest .

run:
	docker run article-wiki:latest
