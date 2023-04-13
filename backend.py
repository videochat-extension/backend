import aioschedule as schedule
import asyncio
import dico
import functools
import httpx
import os
import re
import time
from sanic import Sanic
from sanic.log import logger
from sanic.response import json

app = Sanic("temporary_videochat-extension_backend")
app.config.CORS_ORIGINS = "https://videochat-extension.starbase.wiki"
app.config.OAS = False

old = {"ch": -1, "ed": -1, "ff": -1}


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


async def parse_users(url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            users = re.search(r"It has ([0-9|,]+) \w", resp.text).group(1).replace(',', '')
            users = int(users)
            return users  # import random  # users = random.randint(1,100000)
        else:
            raise BaseException


@catch_exceptions()
async def update():
    api = dico.Client(os.environ["BOT_TOKEN"], base=dico.AsyncHTTPRequest)
    logger.info("begin task")

    ch = await parse_users(os.environ["CHROME"])
    logger.info(f"chrome: {ch}")

    ed = await parse_users(os.environ["EDGE"])
    logger.info(f"edge: {ed}")

    ff = await parse_users(os.environ["FIREFOX"])
    logger.info(f"firefox: {ff}")

    if ch != old["ch"] or ed != old["ed"] or ff != old["ff"]:
        rep = ""
        if ch != old['ch']:
            rep += f"chrome: {old['ch']} -> {ch} (+{ch - old['ch']}). "
        if ed != old['ed']:
            rep += f"edge: {old['ed']} -> {ed} (+{ed - old['ed']}). "
        if ff != old['ff']:
            rep += f"firefox: {old['ff']} -> {ff} (+{ff - old['ff']}). "
        report = await api.request_channel(os.environ["CHANNEL_REPORT"])
        await report.create_message(rep)

        old['ch'] = ch
        old['ed'] = ed
        old['ff'] = ff

        channel = await api.request_channel(os.environ["CHANNEL_STATUS"])
        await channel.edit(name=f"Weekly Users: {'{:,}'.format(ch + ed + ff).replace(',', '.')}")

    logger.info("end task")


schedule.every(8).hours.do(update)


async def background(app):
    await schedule.run_all()
    while True:
        await asyncio.sleep(6)
        await schedule.run_pending()


app.add_task(background(app))


@app.get("/users")
async def get_users(request):
    return json({"users": old['ch'] + old['ed'] + old['ff']})


if __name__ == "__main__":
    app.run(host="0.0.0.0")
