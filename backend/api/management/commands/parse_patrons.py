# parse_users.py
import time
import functools
import logging
import re

import schedule
import dico
import httpx
from django.conf import settings
from django.core import management
from django.core.cache import caches
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def catch_exceptions():
    def catch_exceptions_decorator(job_func):
        @functools.wraps(job_func)
        def wrapper(*args, **kwargs):
            try:
                return job_func(*args, **kwargs)
            except:
                import traceback
                logger.error(traceback.format_exc())

        return wrapper

    return catch_exceptions_decorator


@catch_exceptions()
def update():
    logger.info("begin task")
    management.call_command("parse_patreon")
    logger.info("end task")


def background():
    schedule.run_all()
    while True:
        time.sleep(60)
        schedule.run_pending()


class Command(BaseCommand):
    help = "Parse Users periodically."

    def handle(self, *args, **options):
        logger.info("Scheduling...")

        schedule.every(settings.PARSE_PATRONS_FREQUENCY_MINUTES).minutes.do(update)

        background()
