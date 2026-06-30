from django.db import models
from django.contrib.auth.models import User
from datetime import time
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from datetime import datetime
import re

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, help_text="Description of the group and its activities")
    logo_base64 = models.TextField(blank=True, null=True, help_text="Group logo as base64 string")
    website = models.URLField(blank=True, null=True, help_text="Group's website URL")
    contact_email = models.EmailField(blank=True, null=True, help_text="Primary contact email for the group")
    telegram_channel = models.CharField(max_length=100, blank=True, null=True, help_text="Telegram channel username (without @)")
    telegram_webhook_channel = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="Telegram channel name for webhook posting (without @)",
        verbose_name="Telegram Webhook Channel (without @)"
    )
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('group_detail', args=[str(self.id)])
    
    def get_leadership(self):
        from users.models import GroupRole
        return GroupRole.objects.filter(group=self).order_by('assigned_at')
    
    def get_upcoming_events(self):
        now = timezone.now()
        return self.event_set.filter(
            Event.active_not_ended_q(now),
            status='active',
        ).order_by('date', 'start_time')
    
    def get_past_events(self):
        now = timezone.now()
        return self.event_set.filter(
            Event.active_ended_q(now),
            status='active',
        ).order_by('-date', '-start_time')

class Event(models.Model):
    title = models.CharField(max_length=200)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    date = models.DateField(help_text='First day of the event.')
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Last day of the event. Defaults to the start date when unset.',
    )
    start_time = models.TimeField(null=True, blank=True, default=time(0, 0, 0))
    end_time = models.TimeField(null=True, blank=True, default=time(0, 0, 0))
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Current status of the event"
    )
    AGE_CHOICES = [
        ('none', 'All ages'),
        ('adult', '18+ (Adult)'),
        ('mature', '21+ (Mature)'),
    ]
    age_restriction = models.CharField(
        max_length=10,
        choices=AGE_CHOICES,
        default='none',
        help_text="Age restriction for the event"
    )
    capacity = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Maximum number of attendees. Leave blank for no limit.",
        validators=[MinValueValidator(0)]
    )
    waitlist_enabled = models.BooleanField(default=False, help_text="Enable a waitlist if capacity is reached.")
    attendee_list_public = models.BooleanField(
        default=True,
        help_text="If false, only organizers can see the attendee list."
    )
    enable_rsvp_questions = models.BooleanField(
        default=False,
        help_text="Enable optional RSVP questions for this event."
    )
    question1_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Custom text for RSVP Question 1. Leave blank for default."
    )
    question2_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Custom text for RSVP Question 2. Leave blank for default."
    )
    question3_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Custom text for RSVP Question 3. Leave blank for default."
    )
    accessibility_details = models.TextField(
        blank=True,
        help_text="Describe how this event is accessible. If left blank, event is not marked as accessible."
    )
    
    def clean(self):
        if self.waitlist_enabled and self.capacity is None:
            raise ValidationError({
                'waitlist_enabled': 'Capacity must be set when waitlist is enabled.',
                'capacity': 'Capacity must be set when waitlist is enabled.'
            })
    
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('event_detail', args=[str(self.id)])

    @property
    def effective_end_date(self):
        return self.end_date or self.date

    @classmethod
    def _field(cls, prefix, name):
        return f'{prefix}{name}' if prefix else name

    @classmethod
    def active_not_ended_q(cls, now=None, prefix=''):
        """Events still in progress or not yet started (by end date/time)."""
        now = now or timezone.now()
        today = now.date()
        current_time = now.time()
        end_date = cls._field(prefix, 'end_date')
        date = cls._field(prefix, 'date')
        end_time = cls._field(prefix, 'end_time')
        return (
            models.Q(**{f'{end_date}__gt': today}) |
            models.Q(**{f'{end_date}__isnull': True, f'{date}__gt': today}) |
            (
                (models.Q(**{end_date: today}) | models.Q(**{f'{end_date}__isnull': True, date: today})) &
                models.Q(**{f'{end_time}__gt': current_time})
            )
        )

    @classmethod
    def active_ended_q(cls, now=None, prefix=''):
        """Events whose end date/time has passed."""
        now = now or timezone.now()
        today = now.date()
        current_time = now.time()
        end_date = cls._field(prefix, 'end_date')
        date = cls._field(prefix, 'date')
        end_time = cls._field(prefix, 'end_time')
        return (
            models.Q(**{f'{end_date}__lt': today}) |
            models.Q(**{f'{end_date}__isnull': True, f'{date}__lt': today}) |
            (
                (models.Q(**{end_date: today}) | models.Q(**{f'{end_date}__isnull': True, date: today})) &
                models.Q(**{f'{end_time}__lte': current_time})
            )
        )

    @classmethod
    def overlaps_date_range_q(cls, range_start, range_end, prefix=''):
        """Events overlapping [range_start, range_end) — for calendar views."""
        end_date = cls._field(prefix, 'end_date')
        date = cls._field(prefix, 'date')
        return models.Q(**{f'{date}__lt': range_end}) & (
            models.Q(**{f'{end_date}__gte': range_start}) |
            models.Q(**{f'{end_date}__isnull': True, f'{date}__gte': range_start})
        )

    def _aware_datetime(self, event_date, event_time):
        dt = datetime.combine(event_date, event_time or time(0, 0, 0))
        if timezone.is_aware(timezone.now()):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def get_start_datetime(self):
        return self._aware_datetime(self.date, self.start_time)

    def get_end_datetime(self):
        return self._aware_datetime(self.effective_end_date, self.end_time)

    def has_started(self, now=None):
        now = now or timezone.now()
        return now >= self.get_start_datetime()

    def has_ended(self, now=None):
        now = now or timezone.now()
        return now > self.get_end_datetime()

    @property
    def is_multi_day(self):
        return self.effective_end_date > self.date

    @property
    def rsvps_locked(self):
        """Prevent RSVP changes once the event starts or is cancelled."""
        return self.status != 'active' or self.has_started()

class RSVP(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rsvps', null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)  # Keep for backward compatibility
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('confirmed', 'Confirmed'),
        ('waitlisted', 'Waitlisted'),
        ('maybe', 'Maybe'),
        ('not_attending', 'Not Attending')
    ], default='confirmed', null=True, blank=True)

    # Organizer-only RSVP questions
    question1 = models.CharField(max_length=255, null=True, blank=True, help_text="Organizer-only question 1 (visible only to event organizers)")
    question2 = models.CharField(max_length=255, null=True, blank=True, help_text="Organizer-only question 2 (visible only to event organizers)")
    question3 = models.CharField(max_length=255, null=True, blank=True, help_text="Organizer-only question 3 (visible only to event organizers)")
    
    # Badge customization fields
    accessibility_needs = models.BooleanField(default=False, help_text="Show accessibility indicator on badge")
    custom_rank = models.CharField(max_length=50, null=True, blank=True, help_text="Custom rank/role label for badge (e.g. 'Sponsor', 'VIP', 'Staff')")

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['timestamp'] # Order by timestamp for waitlist purposes

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.event.title}"
        return f"{self.name} - {self.event.title}"

    def remove(self):
        self.delete()

class Post(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    published = models.DateTimeField()
    original_link = models.URLField(blank=True, null=True)
    guid = models.CharField(max_length=255, unique=True, blank=True, null=True)

    def __str__(self):
        return self.title

    def get_excerpt(self, length=200):
        # Remove <img> tags
        text = re.sub(r'<img[^>]*>', '', self.content)
        # Strip other HTML tags
        text = strip_tags(text)
        # Truncate
        if len(text) > length:
            return text[:length] + '…'
        return text
