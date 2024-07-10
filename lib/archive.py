from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from io import BytesIO


def make_zip_data(archive_data: dict) -> bytes:
    """
    Create an in-memory zipfile for export.
    """
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_archive:
        for doc_slug, doc_part in archive_data.items():
            for part_slug, wiki_text in doc_part.items():
                file = ZipInfo(f"{doc_slug}/{part_slug}.txt")
                zip_archive.writestr(file, wiki_text)
    return archive.getvalue()
