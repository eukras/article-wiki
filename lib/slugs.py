from slugify import slugify


def slug(text):
    """
    Eliminate apostrophes from input text so that "it's" becomes 'its' not
    'it-s'.
    """
    return slugify(text.replace("'", ""))
