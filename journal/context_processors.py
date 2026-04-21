from django.conf import settings


def site_settings(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_SHORT_NAME": settings.SITE_SHORT_NAME,
        "SITE_EMAIL": settings.SITE_EMAIL,
        "SITE_PHONE": settings.SITE_PHONE,
        "SITE_ADDRESS": settings.SITE_ADDRESS,
        "HCAPTCHA_SITE_KEY": settings.HCAPTCHA_SITE_KEY,
    }
