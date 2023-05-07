# parse_users.py
import asyncio
import functools
import logging
import re

import aioschedule as schedule
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


async def parse_users(url, regex):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            users = re.search(regex, resp.text).group(1).replace(',', '')
            users = int(users)
            return users
        else:
            raise BaseException


@catch_exceptions()
async def update():
    api = dico.Client(settings.DISCORD_BOT_TOKEN, base=dico.AsyncHTTPRequest)
    logger.info("begin task")

    new = {i: -1 for i in settings.PARSE_USERS.keys()}

    for k, v in settings.PARSE_USERS.items():
        new[k] = await parse_users(v.get('url'), v.get('regex'))
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

        report_channel = await api.request_channel(settings.DISCORD_CHANNEL_REPORT)
        final_report = f"ALL: {old_sum} -> {new_sum} ({new_sum - old_sum:+}). {report}"
        await report_channel.create_message(final_report)

        await caches["users-count"].aset("user-count", new_sum, None)

        status_channel = await api.request_channel(settings.DISCORD_CHANNEL_STATUS)
        await status_channel.edit(name=f"Weekly Users: {new_sum:,}".replace(',', '.'))

    logger.info("end task")


async def background():
    await schedule.run_all()
    while True:
        await asyncio.sleep(60)
        await schedule.run_pending()


class Command(BaseCommand):
    help = "Parse Users periodically."

    def handle(self, *args, **options):
        logger.info("Scheduling...")

        schedule.every(settings.PARSE_USERS_FREQUENCY).hours.do(update)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(background())
