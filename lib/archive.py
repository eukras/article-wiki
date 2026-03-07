from datetime import datetime
from io import BytesIO
from PIL.Image import Image
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from lib.typing import DocumentPart


# -----------------------
# Generate zip file names
# -----------------------


def zip_name() -> str:
    """
    Formats a timestamped archive name for this user_slug.
    """
    name = "article-wiki_{:02d}{:02d}{:02d}_{:02}{:02d}.zip"
    now = datetime.now()
    return name.format(now.year, now.month, now.day, now.hour, now.minute)


def user_zip_name(user_slug: str) -> str:
    """
    Formats a timestamped archive name for this user_slug.
    """
    name = "article-wiki_{:s}_{:02d}{:02d}{:02d}_{:02}{:02d}.zip"
    now = datetime.now()
    return name.format(user_slug, now.year, now.month, now.day, now.hour, now.minute)


def user_document_zip_name(user_slug: str, doc_slug: str) -> str:
    """
    Formats a timestamped archive name for this user_slug.
    """
    name = "article-wiki_{:s}_{:s}_{:02d}{:02d}{:02d}_{:02}{:02d}.zip"
    now = datetime.now()
    return name.format(
        user_slug, doc_slug, now.year, now.month, now.day, now.hour, now.minute
    )


class Archive:
    def __init__(self, data) -> None:
        self.data = data

    # ---------------------------------------
    # Create zipfiles in memory
    # ---------------------------------------

    def zip_site(self) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_archive:
            for user_slug, user_docs in self.data.get_site_user_documents().items():
                for doc_slug, doc_parts in user_docs.items():
                    for file_name, content in doc_parts.items():
                        self.add_file(
                            zip_archive, f"{user_slug}/{doc_slug}/{file_name}", content
                        )
        return buffer.getvalue()

    def zip_user(self, user_slug: str) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_archive:
            for doc_slug, doc_parts in self.data.get_user_document(user_slug).items():
                for file_name, content in doc_parts.items():
                    self.add_file(zip_archive, f"{doc_slug}/{file_name}", content)
        return buffer.getvalue()

    def zip_document(self, user_slug: str, doc_slug: str) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_archive:
            for file_name, content in self.data.get_document(
                user_slug, doc_slug
            ).items():
                self.add_file(zip_archive, file_name, content)
        return buffer.getvalue()

    def add_file(self, zip_archive: ZipFile, path_to_file: str, content: DocumentPart):
        if isinstance(content, Image):
            buffer = BytesIO()
            content.save(buffer, format="PNG")
            zip_archive.writestr(ZipInfo(path_to_file), buffer.getvalue())
        elif isinstance(content, str):
            zip_archive.writestr(ZipInfo(path_to_file), content)
        else:
            raise ValueError(
                f"Document files must be text or Image: {content[:100]} found"
            )
