from django.db import migrations


def create_us_states(apps, schema_editor):
    Country = apps.get_model('events', 'Country')
    State = apps.get_model('events', 'State')
    Event = apps.get_model('events', 'Event')

    us_country, _ = Country.objects.get_or_create(
        alpha_2_code='US',
        defaults={
            'alpha_3_code': 'USA',
            'country_name': 'United States'
        }
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
            }
        )

    for event in Event.objects.all():
        state_value = getattr(event, 'state', None)
        if not state_value:
            continue

        state_value = str(state_value).strip()
        if not state_value:
            continue

        state_obj = None
        try:
            state_obj = State.objects.get(state_name__iexact=state_value)
        except State.DoesNotExist:
            try:
                state_obj = State.objects.get(state_code__iexact=state_value)
            except State.DoesNotExist:
                continue

        event.state_tmp = state_obj
        if not event.country:
            event.country = state_obj.country
            event.save(update_fields=['state_tmp', 'country'])
        else:
            event.save(update_fields=['state_tmp'])


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_event_location'),
    ]

    operations = [
        migrations.RunPython(create_us_states, reverse_func),
        migrations.RemoveField(
            model_name='event',
            name='state',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='state_tmp',
            new_name='state',
        ),
    ]
