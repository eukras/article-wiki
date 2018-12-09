# Install Notes

(Additional to ../INSTALL.txt)

Running Redis in Docker

```bash
bash redis.docker.sh
```

Running python apps in supervisor...

```bash
vim install/etc/supervisor/conf.d/article-wiki.conf
sudo cp install/etc/supervisor/conf.d/article-wiki.conf /etc/supervisor/conf.d/.
sudo supervisorctl start article-wiki
```
