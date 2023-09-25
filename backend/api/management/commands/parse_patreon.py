import requests
import json
import time
import logging
from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Parse Patrons & tiers."

    def handle(self, *args, **options):
        logger.info("Parsing patrons...")

        headers = {'Authorization': f'Bearer {settings.PATREON_ACCESS_TOKEN}'}

        # TODO: add paging page[cursor]
        link = f"https://www.patreon.com/api/oauth2/v2/campaigns/{settings.PATREON_CAMPAIGN_ID}/members?include=user,currently_entitled_tiers&fields[member]=campaign_lifetime_support_cents,currently_entitled_amount_cents,email,full_name,is_follower,last_charge_date,last_charge_status,lifetime_support_cents,next_charge_date,note,patron_status,pledge_cadence,pledge_relationship_start,will_pay_amount_cents"

        response = requests.get(link, headers=headers)

        data = response.json()

        patrons = {}
        for item in data['data']:
            if item['type'] == "member" and item['attributes']['patron_status'] == "active_patron":
                user = item['relationships']['user']['data']['id']
                tier = item['relationships']['currently_entitled_tiers']['data'][0]['id']
                patrons[user] = {
                        'user': user,
                        'tier': tier,
                        'ceac': item['attributes']['currently_entitled_amount_cents']
                        }
        result = {
                'timestamp': int(time.time()),
                'data': patrons
                }

        logging.info(f"Saving {len(patrons)} patrons...")

        caches['patrons'].set('patreon', result, None)
