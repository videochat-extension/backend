from __future__ import annotations

import ipaddress

import httpx
import hmac
import hashlib
import logging
import base64
import json
from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core import management
from django.core.cache import cache, caches
from githubkit import GitHub, AppInstallationAuthStrategy
from django.db.models import F
from django.utils import timezone
from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from rest_framework import status
from rest_framework.decorators import throttle_classes, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Quota, Tier
from .serializers import GeoRequestSerializer, BugReportSerializer, GeoPatronRequestSerializer
from .throttle import GeoRateThrottle, GetUsersRateThrottle, BugReportRateThrottle, PatronRateThrottle 

logger = logging.getLogger(__name__)

async def request_ip_data(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, lang: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://pro.ip-api.com/json/{ip}?fields=17032159&key={settings.IPAPI_KEY}&lang={lang}")
        return r


github = GitHub(AppInstallationAuthStrategy(settings.GH_APP_ID, settings.GH_PR_KEY, settings.GH_INSTL_ID))

async def request_bdc_ip_data(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, lang: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api-bdc.net/data/ip-geolocation-full?ip={ip}&localityLanguage={lang}&key={settings.BDC_KEY}")
        return r


@api_view(['GET'])
@throttle_classes([GeoRateThrottle])
async def geo(request):
    valid = GeoRequestSerializer(data=request.query_params)
    valid.is_valid(raise_exception=True)

    cache_key = f"{valid.validated_data['lang']}-{valid.validated_data['ip']}"
    cached = await cache.aget(cache_key)

    if cached:
        logger.info('cached')
        return Response(cached)
    else:
        r = await request_ip_data(valid.validated_data['ip'], valid.validated_data['lang'])
        if r.status_code == httpx.codes.OK:
            logger.info(r.status_code)
            data = r.json()
            if data["status"] == "success":
                await cache.aset(cache_key, data, settings.IPAPI_CACHE_DURATION)
                return Response(data)
            return Response({"status": "failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            r.raise_for_status()


async def get_quota(user):
    quota_obj, created = await Quota.objects.aget_or_create(
        patreon=(await user.socialaccount_set.alast()),
        usage_time_span__month=timezone.now().month,
        usage_time_span__year=timezone.now().year
    )
    return quota_obj


async def get_plan(user):
    # TODO this should be optimized
    uid = (await user.socialaccount_set.alast()).uid
    patrons = await caches['patrons'].aget('patreon')
    if uid in patrons['data']:
        # get tier
        tier = await Tier.objects.values().aget(plan_id=patrons['data'][uid]['tier'])
        return {
            "allow_wired": tier['allow_wired'],
            "allow_mobile": tier['allow_mobile'],
            "active": True,
            "limit": tier['limit']
        }
    else:
        return {
            "allow_wired": False,
            "allow_mobile": False,
            "active": False,
            "limit": 0
        }


@api_view(['GET'])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
async def whoami(request):
    quota_obj = await get_quota(request.user)
    plan = await get_plan(request.user)
    return Response({
        "username": request.user.username,
        "api_usage_patreon_quota": quota_obj.api_usage_patreon_quota,
        "plan_limit": plan['limit'],
        "uid": (await request.user.socialaccount_set.alast()).uid,
        "allow_wired": plan["allow_wired"],
        "active": plan["active"],
        "allow_mobile": plan["allow_mobile"]
    })

async def inc_quota(pk, key):
    await Quota.objects.select_for_update().filter(id=pk).aupdate(**{key:F(key) + 1})


@api_view(['GET'])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
@throttle_classes([PatronRateThrottle])
async def patron_geo(request):
    valid = GeoPatronRequestSerializer(data=request.query_params)
    valid.is_valid(raise_exception=True)

    plan = await get_plan(request.user)
    if not plan["active"]:
        return Response({"error": "no active patreon subscription"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    quota_obj = await get_quota(request.user)

    cache_key = f"{valid.validated_data['lang_ipapi']}-{valid.validated_data['ip']}"
    cached = await cache.aget(cache_key)
    if cached:
        ipapi_data = cached
    else:
        r = await request_ip_data(valid.validated_data['ip'], valid.validated_data['lang_ipapi'])
        if r.status_code == httpx.codes.OK:
            data = r.json()
            if data["status"] == "success":
                await cache.aset(cache_key, data, settings.IPAPI_CACHE_DURATION)
                ipapi_data = data
            else:
                await inc_quota(quota_obj.id, "api_usage_patreon_ipapi_failed")
                return Response({"status": "failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            await inc_quota(quota_obj.id, "api_usage_patreon_ipapi_failed")
            return Response({"status": "internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    is_mobile = ipapi_data["mobile"]
    bdc_cache_key = f"{valid.validated_data['lang_bdc']}-{valid.validated_data['ip']}"

    if not is_mobile and not valid.validated_data["requestWired"]:
        await inc_quota(quota_obj.id, "api_usage_patreon_not_requested_wired")
        return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": False, "status": "wired not requsted"})

    if is_mobile and not valid.validated_data["requestCellural"]:
        await inc_quota(quota_obj.id, "api_usage_patreon_not_requested_mobile")
        return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": False, "status": "mobile not requested"})

    if is_mobile and not plan["allow_mobile"]:
        await inc_quota(quota_obj.id, "api_usage_patreon_not_allowed_mobile")
        return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": False, "status": "mobile not allowed"})

    if not is_mobile and not plan["allow_wired"]:
        await inc_quota(quota_obj.id, "api_usage_patreon_not_allowed_wired")
        return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": False, "status": "wired not allowed"})

    if quota_obj.api_usage_patreon_quota < plan["limit"]:
        bdc_cache = await caches['bdc-cache'].aget(bdc_cache_key)
        if bdc_cache:
            await caches['bdc-cache'].atouch(bdc_cache_key, settings.BDC_CACHE_TOUCH_DURATION)
            await inc_quota(quota_obj.id, "api_usage_patreon_cached")
            return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": True, "bdc": bdc_cache,
                             "status": "cache was found"})
        else:
            r = await request_bdc_ip_data(valid.validated_data['ip'], valid.validated_data['lang_bdc'])
            if r.status_code == httpx.codes.OK:
                data = r.json()
                await caches['bdc-cache'].aset(bdc_cache_key, data, settings.IPAPI_CACHE_DURATION)
                bdc = data

                await inc_quota(quota_obj.id, "api_usage_patreon_quota")
                return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": True, "bdc": bdc,
                                 "status": "made request"})
            else:
                await inc_quota(quota_obj.id, "api_usage_patreon_bdc_failed")
                return Response({"status": "internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    else:
        bdc_cache = await caches['bdc-cache'].aget(bdc_cache_key)
        if bdc_cache:
            await caches['bdc-cache'].atouch(bdc_cache_key, settings.BDC_CACHE_TOUCH_DURATION)
            await inc_quota(quota_obj.id, "api_usage_patreon_exceeded_found")
            return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": True, "bdc": bdc_cache,
                             "status": "quota exceeded, cache was found"})
        else:
            await inc_quota(quota_obj.id, "api_usage_patreon_exceeded_notfound")
            return Response({"ipapi_data": True, "ipapi": ipapi_data, "bdc_data": False,
                             "status": "quota exceeded, cache not found"})


@api_view(['GET'])
@throttle_classes([GetUsersRateThrottle])
async def get_users(request):
    user_count = await caches['users-count'].aget('user-count', "?")
    dots = request.query_params.get('dots')
    if dots is not None and type(user_count) is int:
        user_count = f"{user_count:,}".replace(',', '.')

    return Response({"users": user_count})


@api_view(['POST'])
@throttle_classes([BugReportRateThrottle])
async def submit_bug(request):
    valid = BugReportSerializer(data=request.data)
    valid.is_valid(raise_exception=True)

    await github.rest.issues.async_create(owner='videochat-extension', repo='videochat-extension',
                                          data={
                                              'title': valid.validated_data['title'],
                                              "body": valid.validated_data['details'],
                                              'assignee': 'qrlk',
                                              'milestone': 1,
                                              'labels': ['google-form']
                                          })

    return Response('ok')


@api_view(['post'])
async def webhook_patreon(request):
    valid = hmac.compare_digest(
        request.META.get('HTTP_X_PATREON_SIGNATURE', str()),
        hmac.new(settings.PATREON_WEBHOOK_SECRET.encode(), request.body, digestmod='md5').hexdigest()
    )
    if valid:
        await sync_to_async(management.call_command)("parse_patreon")

        async with httpx.AsyncClient() as client:
            r = await client.post(settings.WEBHOOK_REPORT, data={'msg': request.META.get('HTTP_X_PATREON_EVENT', str())})

        return Response('ok')
    else:
        return Response('sender is not valid', status=status.HTTP_403_FORBIDDEN)


@api_view(['post'])
async def webhook_canny(request):
    nonce = request.META.get('HTTP_CANNY_NONCE')
    signature = request.META.get('HTTP_CANNY_SIGNATURE')

    hash = hmac.new(
        settings.CANNY_API_KEY.encode('utf-8'),
        msg=nonce.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()

    calculated = base64.b64encode(hash).decode()

    valid = signature == calculated
    if valid:
        settings.CANNY_DISCORD_WEBHOOK
        data = {
                'content':None,
                'attachments': []
                }
        color = None
        if request.data['objectType'] == "post":
            data['embeds'] =[
                    {
                        'title': request.data['object']['title'],
                        'description': request.data['object']['details'],
                        'url': request.data['object']['url'],
                        'author': {
                            'name': 'user'
                            },
                        'footer': {
                            'text': request.data['type']    
                            },
                        'timestamp': request.data['created']
                        }
                    ]

        elif request.data['objectType'] == "comment":
            data['embeds'] = [
                    {
                        'title': request.data['object']['post']['title'],
                        'description': request.data['object']['value'],
                        'url': request.data['object']['post']['url'],
                        'author': {
                            'name': 'user'
                            },
                        'footer': {
                            'text': request.data['type']    
                            },
                        'timestamp': request.data['created']
                        }
                    ]
        elif request.data['objectType'] == "vote":
            data['embeds'] = [
                    {
                        'title': request.data['object']['post']['title'],
                        'url': request.data['object']['post']['url'],
                        'author': {
                            'name': 'user'
                            },
                        'footer': {
                            'text': request.data['type']    
                            },
                        'timestamp': request.data['created']
                        }
                    ]

        if 'deleted' in request.data['type']:
            data['embeds'][0]['color'] = 16711680

        if 'created' in request.data['type']:
            data['embeds'][0]['color'] = 65280

        async with httpx.AsyncClient() as client:
            r = await client.post(settings.CANNY_DISCORD_WEBHOOK, data=json.dumps(data), headers={'content-type':'application/json'})

        return Response('ok')
    else:
        return Response('sender is not valid', status=status.HTTP_403_FORBIDDEN)
