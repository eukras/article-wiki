# README

## EPUB

The `epub_template` folder can be copied and `{KEY}` values substitutes to
create an EPUB v.3 document, which when zipped in a particular way becomes a
downloadable eBook. See `lib/wiki/storage.py` for tools.

```bash
mimetype
META-INF/
   container.xml
OEBPS/
  content.opf
  title.html
  content.html
  stylesheet.css
  toc.ncx
  images/
     cover.png
```
