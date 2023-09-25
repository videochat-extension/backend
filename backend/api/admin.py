from django.contrib import admin
from .models import Tier, Quota


# Register your models here.
@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    pass


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    pass
