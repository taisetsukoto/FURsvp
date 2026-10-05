from datetime import time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from events.forms import EventForm
from events.models import Event, Group, RSVP


class RSVPCloseDateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('organizer', 'o@example.com', 'pass')
        self.group = Group.objects.create(name='Test Group')
        self.today = timezone.localdate()
        self.event = Event.objects.create(
            title='Meetup',
            group=self.group,
            date=self.today + timedelta(days=14),
            start_time=time(18, 0),
            end_time=time(21, 0),
            organizer=self.user,
            state='New York',
            description='A meetup',
        )

    def _form(self, **overrides):
        start = self.today + timedelta(days=10)
        data = {
            'title': 'Later',
            'group': self.group.id,
            'date': start.isoformat(),
            'start_time': '18:00',
            'end_time': '21:00',
            'age_restriction': 'none',
            'description': 'Hello',
            'eula_agreement': 'on',
            'state_agreement': 'on',
            'attendee_list_public': 'on',
        }
        data.update(overrides)
        return EventForm(data=data, user=self.user)

    def test_open_through_the_close_date(self):
        self.event.rsvp_close_date = self.today
        self.event.save()
        self.assertFalse(self.event.rsvp_close_date_passed())
        self.assertFalse(self.event.signups_closed)
        self.assertFalse(self.event.rsvps_locked)

    def test_closed_the_day_after_the_close_date(self):
        self.event.rsvp_close_date = self.today - timedelta(days=1)
        self.event.save()
        self.assertTrue(self.event.rsvp_close_date_passed())
        self.assertTrue(self.event.signups_closed)
        self.assertFalse(self.event.rsvps_locked)

    def test_form_rejects_close_date_after_start(self):
        start = self.today + timedelta(days=10)
        form = self._form(rsvp_close_date=(start + timedelta(days=1)).isoformat())
        self.assertFalse(form.is_valid())
        self.assertIn('rsvp_close_date', form.errors)

    def test_form_accepts_close_date_on_start_date(self):
        start = self.today + timedelta(days=10)
        form = self._form(rsvp_close_date=start.isoformat())
        self.assertTrue(form.is_valid(), form.errors)
        event = form.save(commit=False)
        event.organizer = self.user
        event.save()
        self.assertEqual(event.rsvp_close_date, start)

    def test_new_rsvp_rejected_after_close_date(self):
        self.event.rsvp_close_date = self.today - timedelta(days=1)
        self.event.save()
        attendee = User.objects.create_user('guest', 'g@example.com', 'pass')
        self.client.force_login(attendee)
        response = self.client.post(self.event.get_absolute_url(), {'status': 'confirmed'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.event.rsvps.filter(user=attendee).exists())
        page = self.client.get(self.event.get_absolute_url())
        self.assertContains(page, 'RSVPs closed')

    def test_existing_rsvp_can_be_removed_after_close_date(self):
        self.event.rsvp_close_date = self.today - timedelta(days=1)
        self.event.save()
        attendee = User.objects.create_user('guest', 'g@example.com', 'pass')
        RSVP.objects.create(event=self.event, user=attendee, status='confirmed')
        self.client.force_login(attendee)
        response = self.client.post(self.event.get_absolute_url(), {'remove_rsvp': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.event.rsvps.filter(user=attendee).exists())
