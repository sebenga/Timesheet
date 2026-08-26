from django.db import migrations, models
import django.db.models.deletion


def create_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('tracker', 'UserProfile')
    for user in User.objects.all():
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'must_change_password': False},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('tracker', '0004_timesheetrecord_frozen_margins'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('must_change_password', models.BooleanField(
                    default=False,
                    help_text='Require this user to set a new password on next login.',
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to='auth.user',
                )),
            ],
        ),
        migrations.RunPython(create_profiles, migrations.RunPython.noop),
    ]
