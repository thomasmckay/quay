#!/usr/bin/env python

from datetime import datetime, timedelta
from urllib.parse import urlunparse

from jinja2 import Template
from cachetools.func import lru_cache

import logging
import release
import os.path

from app import app
from data.model import ServiceKeyDoesNotExist
from data.model.release import set_region_release
from data.model.service_keys import get_service_key
from util.config.database import sync_database_with_config
from util.generatepresharedkey import generate_key
from _init import CONF_DIR


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_audience():
    scheme = app.config.get("PREFERRED_URL_SCHEME")
    hostname = app.config.get("SERVER_HOSTNAME")

    # hostname includes port, use that
    if ":" in hostname:
        return urlunparse((scheme, hostname, "", "", "", ""))

    # no port, guess based on scheme
    if scheme == "https":
        port = "443"
    else:
        port = "80"

    return urlunparse((scheme, hostname + ":" + port, "", "", "", ""))


def _verify_service_key():
    try:
        with open(app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"]) as f:
            quay_key_id = f.read()

        try:
            get_service_key(quay_key_id, approved_only=False)
            assert os.path.exists(app.config["INSTANCE_SERVICE_KEY_LOCATION"])
            return quay_key_id
        except ServiceKeyDoesNotExist:
            logger.exception(
                "Could not find non-expired existing service key %s; creating a new one",
                quay_key_id,
            )
            return None

        # Found a valid service key, so exiting.
    except IOError:
        logger.exception("Could not load existing service key; creating a new one")
        return None


def main():
    if not app.config.get("SETUP_COMPLETE", False):
        raise Exception(
            "Your configuration bundle is either not mounted or setup has not been completed"
        )

    sync_database_with_config(app.config)

    # Record deploy
    if release.REGION and release.GIT_HEAD:
        set_region_release(release.SERVICE, release.REGION, release.GIT_HEAD)


if __name__ == "__main__":
    main()
