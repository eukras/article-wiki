from typing import Union
from PIL.Image import Image


type DocumentPart = Union[str, Image]

type DocumentParts = dict[str, DocumentPart]

type UserDocuments = dict[str, DocumentParts]

type SiteUserDocuments = dict[str, UserDocuments]
