# parse_users.py
import time
import functools
import logging
import re

import schedule
import dico
import httpx
from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

old = {i: -1 for i in settings.PARSE_USERS.keys()}


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


def parse_users(url, regex):
    with httpx.Client() as client:
        resp = client.get(url)
        if resp.status_code == 200:
            users = re.search(regex, resp.text).group(1).replace(',', '')
            users = int(users)
            return users
        else:
            raise BaseException


@catch_exceptions()
def update():
    api = dico.APIClient(settings.DISCORD_BOT_TOKEN, base=dico.HTTPRequest)
    logger.info("begin task")

    new = {i: -1 for i in settings.PARSE_USERS.keys()}

    for k, v in settings.PARSE_USERS.items():
        new[k] = parse_users(v.get('url'), v.get('regex'))
        logger.info(f"{k}: {new[k]} ({new[k] - old[k]:+})")

    need_to_report = False
    report = ""
    for k in settings.PARSE_USERS.keys():
        if new[k] != old[k]:
            report += f"{k.capitalize()}: {old[k]} -> {new[k]} ({new[k] - old[k]:+}). "
            need_to_report = True

    if need_to_report:
        old_sum = sum(old.values())
        new_sum = sum(new.values())

        for key in old.keys():
            old[key] = new[key]

        report_channel = api.request_channel(settings.DISCORD_CHANNEL_REPORT)
        final_report = f"ALL: {old_sum} -> {new_sum} ({new_sum - old_sum:+}). {report}"
        report_channel.create_message(final_report)

        caches["users-count"].set("user-count", new_sum, None)

        status_channel = api.request_channel(settings.DISCORD_CHANNEL_STATUS)
        status_channel.edit(name=f"Weekly Users: {new_sum:,}".replace(',', '.'))

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

        schedule.every(settings.PARSE_USERS_FREQUENCY).hours.do(update)

        background()
