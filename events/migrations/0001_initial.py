import datetime

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_us_locations(apps, schema_editor):
    Country = apps.get_model('events', 'Country')
    State = apps.get_model('events', 'State')

    us_country, _ = Country.objects.get_or_create(
        alpha_2_code='US',
        defaults={
            'alpha_3_code': 'USA',
            'country_name': 'United States',
        },
    )

    us_states = [
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
        ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
        ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
        ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
        ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
    ]

    for state_code, state_name in us_states:
        State.objects.get_or_create(
            state_code=state_code,
            defaults={
                'country': us_country,
                'state_name': state_name,
            },
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('alpha_2_code', models.CharField(max_length=2, primary_key=True, serialize=False)),
                ('alpha_3_code', models.CharField(blank=True, max_length=3, null=True, unique=True)),
                ('country_name', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Country',
                'verbose_name_plural': 'Countries',
            },
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, help_text='Description of the group and its activities')),
                ('logo_base64', models.TextField(blank=True, help_text='Group logo as base64 string', null=True)),
                ('website', models.URLField(blank=True, help_text="Group's website URL", null=True)),
                ('contact_email', models.EmailField(blank=True, help_text='Primary contact email for the group', max_length=254, null=True)),
                ('telegram_channel', models.CharField(blank=True, help_text='Telegram channel username (without @)', max_length=100, null=True)),
                ('telegram_webhook_channel', models.CharField(blank=True, help_text='Telegram channel name for webhook posting (without @)', max_length=100, null=True, verbose_name='Telegram Webhook Channel (without @)')),
            ],
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('content', models.TextField()),
                ('published', models.DateTimeField()),
                ('original_link', models.URLField(blank=True, null=True)),
                ('guid', models.CharField(blank=True, max_length=255, null=True, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='State',
            fields=[
                ('state_code', models.CharField(max_length=2, primary_key=True, serialize=False)),
                ('state_name', models.CharField(max_length=100)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='states', to='events.country')),
            ],
            options={
                'verbose_name': 'State',
                'verbose_name_plural': 'States',
                'ordering': ['country__alpha_2_code', 'state_name'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('date', models.DateField()),
                ('start_time', models.TimeField(blank=True, default=datetime.time(0, 0), null=True)),
                ('end_time', models.TimeField(blank=True, default=datetime.time(0, 0), null=True)),
                ('description', models.TextField(blank=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=50, null=True)),
                ('timezone', models.CharField(blank=True, help_text='IANA time zone for the event location', max_length=50, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('cancelled', 'Cancelled')], default='active', help_text='Current status of the event', max_length=20)),
                ('age_restriction', models.CharField(choices=[('none', 'All ages'), ('adult', '18+ (Adult)'), ('mature', '21+ (Mature)')], default='none', help_text='Age restriction for the event', max_length=10)),
                ('capacity', models.IntegerField(blank=True, help_text='Maximum number of attendees. Leave blank for no limit.', null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('waitlist_enabled', models.BooleanField(default=False, help_text='Enable a waitlist if capacity is reached.')),
                ('attendee_list_public', models.BooleanField(default=True, help_text='If false, only organizers can see the attendee list.')),
                ('enable_rsvp_questions', models.BooleanField(default=False, help_text='Enable optional RSVP questions for this event.')),
                ('question1_text', models.CharField(blank=True, default='', help_text='Custom text for RSVP Question 1. Leave blank for default.', max_length=255)),
                ('question2_text', models.CharField(blank=True, default='', help_text='Custom text for RSVP Question 2. Leave blank for default.', max_length=255)),
                ('question3_text', models.CharField(blank=True, default='', help_text='Custom text for RSVP Question 3. Leave blank for default.', max_length=255)),
                ('accessibility_details', models.TextField(blank=True, help_text='Describe how this event is accessible. If left blank, event is not marked as accessible.')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.group')),
                ('organizer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='event',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='events.country'),
        ),
        migrations.AddField(
            model_name='event',
            name='state',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='events.state'),
        ),
        migrations.CreateModel(
            name='RSVP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(blank=True, choices=[('confirmed', 'Confirmed'), ('waitlisted', 'Waitlisted'), ('maybe', 'Maybe'), ('not_attending', 'Not Attending')], default='confirmed', max_length=20, null=True)),
                ('question1', models.CharField(blank=True, help_text='Organizer-only question 1 (visible only to event organizers)', max_length=255, null=True)),
                ('question2', models.CharField(blank=True, help_text='Organizer-only question 2 (visible only to event organizers)', max_length=255, null=True)),
                ('question3', models.CharField(blank=True, help_text='Organizer-only question 3 (visible only to event organizers)', max_length=255, null=True)),
                ('accessibility_needs', models.BooleanField(default=False, help_text='Show accessibility indicator on badge')),
                ('custom_rank', models.CharField(blank=True, help_text="Custom rank/role label for badge (e.g. 'Sponsor', 'VIP', 'Staff')", max_length=50, null=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rsvps', to='events.event')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rsvps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['timestamp'],
                'unique_together': {('event', 'user')},
            },
        ),
        migrations.RunPython(seed_us_locations, migrations.RunPython.noop),
    ]
