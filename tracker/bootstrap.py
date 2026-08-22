from django.contrib.auth.models import User

from .models import TimesheetRecord

ADMIN_USERNAME = 'sikidosi'
ADMIN_PASSWORD = 'Intokazi01'
ADMIN_EMAIL = 'sikidosi@atisa.co.za'
LEGACY_ADMIN_USERNAME = 'sikidosi@atisa.co.za'


def _migrate_assigned_username(old_username, new_username):
    for record in TimesheetRecord.objects.all():
        values = record.field_values or {}
        if values.get('Assigned') != old_username:
            continue
        values['Assigned'] = new_username
        record.field_values = values
        record.save(update_fields=['field_values'])


def ensure_admin_user():
    user = User.objects.filter(username=ADMIN_USERNAME).first()
    if user is None:
        user = User.objects.filter(username=LEGACY_ADMIN_USERNAME).first()

    if user is None:
        user = User.objects.create_user(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
        )
    else:
        if user.username != ADMIN_USERNAME:
            _migrate_assigned_username(user.username, ADMIN_USERNAME)
            user.username = ADMIN_USERNAME
        user.set_password(ADMIN_PASSWORD)
        user.email = ADMIN_EMAIL

    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    _migrate_assigned_username(LEGACY_ADMIN_USERNAME, ADMIN_USERNAME)
    return user
