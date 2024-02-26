"""
Data manages all operations relating to the key-value store, which
is a Redis database.

General naming is {object}_{verb}(). These functions are obvious
enough not to need individual documentation besides type hints.
See tests for more, at `lib/test/test_data.py`.

Verbs:
    key, set, exists, get, delete, list, count, ...

Objects:

    - user: records (hash)
    - userSet: list of all user_slugs (zset)
    - userDocument: records (hash)
    - userDocumentSet: list of all document records (zset)
    - userDocumentMetadata: for homepage summary (hash)
    - userDocumentLastChanged: (list) trimmed to 10
    - userDocumentCache: key

Using this object as a context manager will execute all the operations in that
group atomically:

with data as _:
    _.userDocument_delete(user_slug, doc_slug)
    _.userDocumentSet_delete(user_slug, doc_slug)
    _.userDocumentMetadata_delete(user_slug, doc_slug)
    _.userDocumentCache_delete(user_slug, doc_slug)
"""

import os
import time
import uuid

import redis

from typing import Dict, List, Union

from lib.slugs import slug
from lib.wiki.utils import random_slug


LAST_CHANGED_MAX = 10


def load_env_config() -> dict:
    """
    Create a config array from environment variables with sensible defaults;
    override with ENV vars in setup.

    @todo: Add an 'ARTICLE_WIKI_' prefix?
    """
    env_defaults = {
            'ADMIN_USER': 'admin',
            'ADMIN_USER_PASSWORD': 'password',
            'APP_HASH': '1111111111',
            'APP_NAME': 'Article Wiki',
            'ARTICLE_WIKI_CREDIT': 'YES',
            'ARTICLE_WIKI_URL': 'https://github.com/eukras/article-wiki',
            'GOOGLE_ANALYTICS_TRACKING_ID': '',
            'PUBLIC_DIR': '/static',
            'REDIS_DATABASE': '0',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_USER': 'default',
            'REDIS_PASSWORD': 'password',
            'REDIS_TEST_DATABASE': '1',
            'SINGLE_USER': 'YES',
            'TIME_ZONE': 'Australia/Sydney',
            'UPLOAD_LIMIT_KB': '500',
            'WEB_HOST': 'localhost',
            'WEB_HOST_PORT': '8080',
        }
    config = {}
    for key, value in env_defaults.items():
        config[key] = os.environ.get(key, value)

    # Extras
    config['SITE'] = "https://" + config['WEB_HOST']
    if config['WEB_HOST_PORT'] not in ['80', '443']:
        config['SITE'] += ":" + config['WEB_HOST_PORT']

    return config


class Data(object):
    """
    Provide a sensible and consistent interface to the underlying Redis
    structures.
    """

    def __init__(self, config: dict, strict: bool = False):
        self.admin_user = config['ADMIN_USER']
        self.redis = redis.Redis(
            config['REDIS_HOST'],
            port=config['REDIS_PORT'],
            username=config['REDIS_USER'],
            password=config['REDIS_PASSWORD'],
            db=config['REDIS_DATABASE'],
            decode_responses=True
        )
        self.redis_binary = redis.Redis(
            config['REDIS_HOST'],
            port=config['REDIS_PORT'],
            username=config['REDIS_USER'],
            password=config['REDIS_PASSWORD'],
            db=config['REDIS_DATABASE']
        )
        self.time_zone = config['TIME_ZONE']
        self.strict = bool(strict)

    # ------------------
    # Pipeline Functions
    # ------------------

    def __enter__(self):
        """
        Replace self.redis with a pipeline; so all Data functions will now
        accumulate and run atomically.
        """
        self.backup_redis_connection = self.redis
        self.redis = self.redis.pipeline()
        return self

    def __exit__(self, *args):
        """
        Execute the pipeline; restore normal self.redis.
        """
        self.redis.execute()
        self.redis = self.backup_redis_connection

    def require_not_in_context_manager(self):
        """
        Using get/list statements inside a context manager won't work, as
        they wont' be executed until the end of the __exit__.

        Raises:
            RuntimeError
        """
        if isinstance(self.redis, redis.client.Pipeline):
            msg = "Get/list operation was called inside a context manager."
            raise RuntimeError(msg)

    # -----------------
    # Utility Functions
    # -----------------

    def check_slugs(self, *slugs):
        if self.strict:
            for _ in slugs:
                if not isinstance(_, str):
                    raise ValueError("Slugs must be strings")
                if _ != slug(_):
                    raise ValueError("Invalid slug: " + _)

    def get_hashes(self, keys: List[str]) -> List[dict]:
        pipe = self.redis.pipeline()
        for key in keys:
            pipe.hgetall(key)  # <-- Returns {} if no key found, so:
        hashes = [_ for _ in pipe.execute() if _ != {}]
        return hashes

    def del_keys(self, keys: List[str]):
        for key in keys:
            self.redis.delete(key)

    def keys_by_prefix(self, prefix: str) -> List[str]:
        return self.redis.keys(prefix + '*')

    # --------------
    # Authentication
    # --------------

    def login_create(self, user_slug: str, user_password: str):
        if self.user_exists(user_slug):
            raise ValueError("User {:s} exists.".format(user_slug))
        key = self.user_key(user_slug)
        user = {'slug': user_slug, 'password': user_password, 'private': 'NO'}
        self.redis.hmset(key, user)

    def login_key(self, token: str):
        return "a:{:s}".format(token)

    def login_set(self, user: dict):
        token = uuid.uuid4().hex
        key = self.login_key(token)
        self.redis.hmset(key, user)
        return token

    def login_get(self, token: str):
        self.require_not_in_context_manager()
        if isinstance(token, str):
            record = self.redis.hgetall(
                self.login_key(token)
            )
            if len(record) > 0:
                return record
        return None

    def login_delete(self, token):
        if isinstance(token, str):
            self.redis.delete(
                self.login_key(token)
            )

    # -----------------
    # Userset Functions
    # -----------------

    def userSet_key(self) -> str:
        return "us"

    def userSet_set(self, user_slug: str):
        key = self.userSet_key()
        self.redis.zadd(key, {user_slug: time.time()})

    def userSet_exists(self, user_slug: str) -> bool:
        key = self.userSet_key()
        rank = self.redis.zrank(key, user_slug)
        return isinstance(rank, int)

    def userSet_get(self, user_slug: str):
        raise NotImplementedError("Use user_get.")

    def userSet_delete(self, user_slug: str):
        key = self.userSet_key()
        self.redis.zrem(key, user_slug)

    def userSet_list(self):
        self.require_not_in_context_manager()
        key = self.userSet_key()
        return self.redis.zrange(key, 0, -1)

    def userSet_count(self):
        self.require_not_in_context_manager()
        return self.redis.zcard(
            self.userSet_key()
        )

    # --------------
    # User Functions
    # --------------

    def user_key(self, user_slug: str) -> str:
        self.check_slugs(user_slug)
        return "u:" + user_slug

    def user_exists(self, user_slug: str) -> bool:
        self.require_not_in_context_manager()
        return self.redis.exists(
            self.user_key(user_slug)
        )

    def user_set(self, user_slug: str, user: dict):
        key = self.user_key(user_slug)
        self.redis.hmset(key, user)
        self.userSet_set(user_slug)

    def user_get(self, user_slug: str) -> Union[dict, None]:
        self.require_not_in_context_manager()
        record = self.redis.hgetall(
            self.user_key(user_slug)
        )
        return record if len(record) > 0 else None

    def user_delete(self, user_slug: str):
        if not self.user_exists(user_slug):
            msg = "User '{:s}' does not exist."
            raise ValueError(msg.format(user_slug))
        self.redis.delete(
            self.user_key(user_slug)
        )

    def user_hash(self) -> Dict[str, hash]:
        """
        v.0.1.0: TODO: Upgrade to allow pagination.
        """
        return {
            user_slug: self.user_get(user_slug)
            for user_slug in self.userSet_list()
        }

    # ------------------
    # User Document Sets
    # ------------------

    def userDocumentSet_key(self, user_slug: str):
        self.check_slugs(user_slug)
        return "uds:" + user_slug

    def userDocumentSet_set(self, user_slug: str, doc_slug: str):
        key = self.userDocumentSet_key(user_slug)
        self.redis.zadd(key, {doc_slug: time.time()})

    def userDocumentSet_exists(self, user_slug: str, doc_slug: str) -> bool:
        key = self.userDocumentSet_key(user_slug)
        rank = self.redis.zrank(key, doc_slug)
        return isinstance(rank, int)

    def userDocumentSet_get(self, user_slug: str):
        raise NotImplementedError("Use userDocument_get.")

    def userDocumentSet_list(self, user_slug: str) -> List[str]:
        key = self.userDocumentSet_key(user_slug)
        return self.redis.zrange(key, 0, -1)

    def userDocumentSet_delete(self, user_slug: str, doc_slug: str):
        key = self.userDocumentSet_key(user_slug)
        self.redis.zrem(key, doc_slug)

    def userDocumentSet_count(self, user_slug: str) -> str:
        return self.redis.zcard(
            self.userDocumentSet_key(user_slug)
        )

    # --------------
    # User Documents
    # --------------

    def userDocument_key(self, user_slug: str, doc_slug: str):
        self.check_slugs(user_slug, doc_slug)
        return "ud:%s:%s" % (user_slug, doc_slug)

    def userDocument_exists(self, user_slug: str, doc_slug: str):
        self.require_not_in_context_manager()
        key = self.userDocument_key(user_slug, doc_slug)
        return self.redis.exists(key)

    def userDocument_unique_slug(self, user_slug: str, base_slug: str) -> str:
        """
        Given a base_slug, try randomised suffixes until one is
        unique. Collisions should be rare, but there is a 1000-tries
        sanity check.
        """
        n = 0
        test_slug = base_slug
        while n < 1000:
            if self.userDocument_exists(user_slug, test_slug):
                test_slug = random_slug(base_slug + "-")
            else:
                return test_slug
            n += 1
        raise ValueError('A unique doc_slug could not be created.')

    def userDocument_get(self,
                         user_slug: str,
                         doc_slug: str) -> Union[dict, None]:
        self.require_not_in_context_manager()
        key = self.userDocument_key(user_slug, doc_slug)
        record = self.redis.hgetall(key)
        return record if len(record) > 0 else None

    def userDocument_set(self,
                         user_slug: str,
                         doc_slug: str,
                         doc_parts: dict,
                         metadata: Union[dict, None] = None):
        key = self.userDocument_key(user_slug, doc_slug)
        self.redis.delete(key)
        self.redis.hmset(key, doc_parts)

        # Dependencies
        self.userSet_set(user_slug)
        self.userDocumentSet_set(user_slug, doc_slug)
        if metadata:
            self.userDocumentMetadata_set(user_slug, doc_slug, metadata)
        if doc_slug not in ['fixtures', 'templates']:
            self.userDocumentLastChanged_set(user_slug, doc_slug)

    def userDocument_delete(self, user_slug: str, doc_slug: str):
        """
        In SINGLE_USER mode (v.0.1.0) there's no need to pipeline these
        commands. Using the standalone functions...

        To Do:
            Upgrade.
        """
        self.redis.delete(
            self.userDocument_key(user_slug, doc_slug)
        )

    def userDocument_list(self, user_slug: str) -> List[hash]:
        self.require_not_in_context_manager()
        return [
            self.userDocument_get(user_slug, doc_slug)
            for doc_slug in self.userDocumentSet_list(user_slug)
        ]

    def userDocument_hash(self, user_slug: str) -> Dict[str, hash]:
        """
        Like userDocument_list, but returns a hash of
        {doc_slug: userDocument}, as might from an export.

        @todo: Restrict downloads to visible documents?
        """
        self.require_not_in_context_manager()
        return {
            doc_slug: self.userDocument_get(user_slug, doc_slug)
            for doc_slug in self.userDocumentSet_list(user_slug)
        }

    # -----------------
    # DOCUMENT METADATA
    # -----------------

    def userDocumentMetadata_key(self, user_slug: str, doc_slug: str) -> str:
        self.check_slugs(user_slug, doc_slug)
        return "udm:{:s}:{:s}".format(user_slug, doc_slug)

    def userDocumentMetadata_exists(self,
                                    user_slug: str,
                                    doc_slug: str) -> bool:
        self.require_not_in_context_manager()
        return self.redis.exists(
            self.userDocumentMetadata_key(user_slug, doc_slug)
        )

    def userDocumentMetadata_get(self,
                                 user_slug: str,
                                 doc_slug: str) -> dict:
        self.require_not_in_context_manager()
        # hgetall returns an empty hash if no match
        record = self.redis.hgetall(
            self.userDocumentMetadata_key(user_slug, doc_slug)
        )
        return record if len(record) > 0 else None

    def userDocumentMetadata_set(self,
                                 user_slug: str,
                                 doc_slug: str,
                                 metadata: dict):
        self.userDocumentSet_set(user_slug, doc_slug)
        udmk = self.userDocumentMetadata_key(user_slug, doc_slug)
        self.redis.delete(udmk)  # <-- Or else it merges
        self.redis.hmset(udmk, metadata)

    def userDocumentMetadata_delete(self, user_slug: str, doc_slug: str):
        self.redis.delete(
            self.userDocumentMetadata_key(user_slug, doc_slug)
        )

    # ------------
    # LAST CHANGED
    # ------------
    # Stores metadata keys for most recently changed docs in a fixed-length
    # list, both globally (for homepage) and for each user homepage.

    def userDocumentLastChanged_key(self, user_slug: str) -> str:
        self.check_slugs(user_slug)
        return "udlc:{:s}".format(user_slug)

    def userDocumentLastChanged_exists(self, user_slug: str) -> str:
        raise NotImplementedError("Use: userDocumentLastChanged_list().")

    def userDocumentLastChanged_set(self,
                                    user_slug: str,
                                    old_doc_slug: str,
                                    new_doc_slug: Union[str, None] = None):
        use_doc_slug = old_doc_slug if new_doc_slug is None else new_doc_slug

        old_metadata_key = self.userDocumentMetadata_key(
            user_slug, old_doc_slug)
        new_metadata_key = self.userDocumentMetadata_key(
            user_slug, use_doc_slug)

        key = self.userDocumentLastChanged_key(user_slug)

        self.redis.lrem(key, LAST_CHANGED_MAX, old_metadata_key)
        self.redis.lpush(key, new_metadata_key)  # <-- L for left push
        self.redis.ltrim(key, 0, LAST_CHANGED_MAX)

    def userDocumentLastChanged_list(self, user_slug: str) -> list:
        self.require_not_in_context_manager()
        key = self.userDocumentLastChanged_key(user_slug)
        return self.get_hashes(
            self.redis.lrange(key, 0, 10)
        )

    def userDocumentLastChanged_delete(self, user_slug: str, doc_slug: str):
        self.redis.lrem(
            self.userDocumentLastChanged_key(user_slug),
            1,
            self.userDocumentMetadata_key(user_slug, doc_slug)
        )

    # -------
    # CACHING
    # -------

    def userDocumentCache_key(self, user_slug: str, doc_slug: str):
        self.check_slugs(user_slug, doc_slug)
        return "udc:{:s}:{:s}".format(user_slug, doc_slug)

    def userDocumentCache_exists(self, user_slug: str, doc_slug: str) -> bool:
        self.require_not_in_context_manager()
        return self.redis.exists(
            self.userDocumentCache_key(user_slug, doc_slug)
        )

    def userDocumentCache_get(self,
                              user_slug: str,
                              doc_slug: str) -> Union[dict, None]:
        self.require_not_in_context_manager()
        return self.redis.get(
            self.userDocumentCache_key(user_slug, doc_slug)
        )

    def userDocumentCache_set(self,
                              user_slug: str,
                              doc_slug: str,
                              text: str):
        key = self.userDocumentCache_key(user_slug, doc_slug)
        self.redis.set(key, text)

    def userDocumentCache_delete(self, user_slug: str, doc_slug: str):
        self.redis.delete(
            self.userDocumentCache_key(user_slug, doc_slug)
        )

    # ----------
    # GENERATION
    # ----------

    # Set a placeholder to say that we're caching epubs...
    # Can be adapted to images.

    def epubCachePlaceholder_key(self, user_slug: str, doc_slug: str):
        self.check_slugs(user_slug, doc_slug)
        return "udep:{:s}:{:s}".format(user_slug, doc_slug)

    def epubCachePlaceholder_exists(
            self, user_slug: str, doc_slug: str) -> bool:
        self.require_not_in_context_manager()
        return self.redis.exists(
            self.epubCachePlaceholder_key(user_slug, doc_slug)
        )

    def epubCachePlaceholder_get(
            self, user_slug: str, doc_slug: str) -> Union[dict, None]:
        self.require_not_in_context_manager()
        return self.redis.get(
            self.epubCachePlaceholder_key(user_slug, doc_slug)
        )

    def epubCachePlaceholder_set(self, user_slug: str, doc_slug: str):
        key = self.epubCachePlaceholder_key(user_slug, doc_slug)
        self.redis.set(key, 'placeholder')

    def epubCachePlaceholder_delete(self, user_slug: str, doc_slug: str):
        self.redis.delete(
            self.epubCachePlaceholder_key(user_slug, doc_slug)
        )

    # Cache epubs...

    def epubCache_key(self, user_slug: str, doc_slug: str):
        self.check_slugs(user_slug, doc_slug)
        return "udec:{:s}:{:s}".format(user_slug, doc_slug)

    def epubCache_exists(self, user_slug: str, doc_slug: str) -> bool:
        self.require_not_in_context_manager()
        return self.redis.exists(
            self.epubCache_key(user_slug, doc_slug)
        )

    def epubCache_get(self, user_slug: str,
                      doc_slug: str) -> Union[dict, None]:
        self.require_not_in_context_manager()
        return self.redis_binary.get(
            self.epubCache_key(user_slug, doc_slug)
        )

    def epubCache_set(self, user_slug: str, doc_slug: str, text: str):
        key = self.epubCache_key(user_slug, doc_slug)
        self.redis_binary.set(key, text, ex=3600)  # <-- keep for an hour

    def epubCache_delete(self, user_slug: str, doc_slug: str):
        self.redis.delete(
            self.epubCache_key(user_slug, doc_slug)
        )

    def epubCache_deleteAll(self):
        for user_slug in self.userSet_list():
            for doc_slug in self.userDocumentSet_list(user_slug):
                self.epubCache_delete(user_slug, doc_slug)
