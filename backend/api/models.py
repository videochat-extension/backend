from allauth.socialaccount.models import SocialAccount
from django.db import models
from django.db.models import SET_NULL

class Quota(models.Model):
    patreon = models.ForeignKey(on_delete=SET_NULL, to=SocialAccount, null=True)
    usage_time_span = models.DateField(auto_now_add=True)
    api_usage_patreon_quota = models.IntegerField(default=0)
    api_usage_patreon_cached = models.IntegerField(default=0)
    api_usage_patreon_exceeded_notfound = models.IntegerField(default=0)
    api_usage_patreon_exceeded_found = models.IntegerField(default=0)
    api_usage_patreon_not_allowed_mobile = models.IntegerField(default=0)
    api_usage_patreon_not_allowed_wired = models.IntegerField(default=0)
    api_usage_patreon_not_requested_mobile = models.IntegerField(default=0)
    api_usage_patreon_not_requested_wired = models.IntegerField(default=0)
    api_usage_patreon_ipapi_failed = models.IntegerField(default=0)
    api_usage_patreon_bdc_failed = models.IntegerField(default=0)

class Tier(models.Model):
    plan_name = models.CharField(max_length=20)
    plan_id = models.IntegerField(default=0)
    limit = models.IntegerField(default=0)
    allow_wired = models.BooleanField()
    allow_mobile = models.BooleanField()
