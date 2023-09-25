from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class PatronRateThrottle(UserRateThrottle):
    scope = 'patron-geolocation'
    rate = '180/min'

class GeoRateThrottle(AnonRateThrottle):
    scope = 'geolocation'
    rate = '90/min'


class GetUsersRateThrottle(AnonRateThrottle):
    scope = 'users'
    rate = '20/min'

class BugReportRateThrottle(AnonRateThrottle):
    scope = 'report-bug'
    rate = '10/min'

