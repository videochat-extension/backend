from __future__ import annotations

import ipaddress

import httpx
from adrf.decorators import api_view
from django.conf import settings
from django.core.cache import cache, caches
from rest_framework import status
from rest_framework.decorators import throttle_classes
from rest_framework.response import Response

from .serializers import GeoRequestSerializer
from .throttle import GeoRateThrottle, GetUsersRateThrottle


async def request_ip_data(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, lang: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"http://ip-api.com/json/{ip}?fields=17032159&lang={lang}")
        return r


@api_view(['GET'])
@throttle_classes([GeoRateThrottle])
async def geo(request):
    valid = GeoRequestSerializer(data=request.query_params)
    valid.is_valid(raise_exception=True)

    cache_key = f"{valid.validated_data['lang']}-{valid.validated_data['ip']}"
    cached = await cache.aget(cache_key)

    if cached:
        return Response(cached)
    else:
        r = await request_ip_data(valid.validated_data['ip'], valid.validated_data['lang'])
        if r.status_code == httpx.codes.OK:
            data = r.json()
            if data["status"] == "success":
                await cache.aset(cache_key, data, settings.IPAPI_CACHE_DURATION)
                return Response(data)
            return Response({"status": "failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            r.raise_for_status()


@api_view(['GET'])
@throttle_classes([GetUsersRateThrottle])
async def get_users(request):
    user_count = await caches['users-count'].aget('user-count', "?")
    dots = request.query_params.get('dots')
    if dots is not None and type(user_count) is int:
        user_count = f"{user_count:,}".replace(',', '.')

    return Response({"users": user_count})
