"""App configuration for HR records."""

from django.apps import AppConfig


class HrRecordsConfig(AppConfig):
    """Django app configuration for HR records app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "hr_records"
