from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from users.models import BannedUser, Notification


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def normalize_notification_link(link):
    """Map legacy/API notification URLs to user-facing pages."""
    if not link:
        return link

    notifications_api_path = reverse('get_notifications').rstrip('/')
    notifications_page_path = reverse('notifications_page')

    if '://' in link:
        path = urlparse(link).path
    else:
        path = link.split('?')[0].split('#')[0]

    if path.rstrip('/') in ('/users/notifications', notifications_api_path):
        return notifications_page_path
    return link

def create_notification(user, message, link=None, event_name=None):
    """
    Creates a new notification for the specified user.
    """
    Notification.objects.create(
        user=user,
        message=message,
        link=normalize_notification_link(link),
        event_name=event_name,
    )

def approve_all_logged_in_users():
    from users.models import Profile
    users = User.objects.exclude(last_login=None)
    for user in users:
        if hasattr(user, 'profile') and not user.profile.is_verified:
            user.profile.is_verified = True
            user.profile.save()


def user_is_sitewide_banned(user):
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return False
    return BannedUser.objects.filter(
        user=user, group__isnull=True, organizer__isnull=True
    ).exists()


def user_is_banned_from_group(user, group):
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated or not group:
        return False
    return BannedUser.objects.filter(user=user, group=group).exists()


def user_is_banned_by_organizer(user, organizer):
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated or not organizer:
        return False
    return BannedUser.objects.filter(user=user, organizer=organizer).exists()


def user_is_banned_from_event(user, event):
    if not user or not getattr(user, 'is_authenticated', False) or not user.is_authenticated:
        return False
    if user_is_sitewide_banned(user):
        return True
    if event.group and user_is_banned_from_group(user, event.group):
        return True
    if event.organizer and user_is_banned_by_organizer(user, event.organizer):
        return True
    return False


def user_event_ban_message(user, event):
    if user_is_sitewide_banned(user):
        return 'You are banned from RSVPing to events on this site.'
    if event.group and user_is_banned_from_group(user, event.group):
        return f'You are banned from RSVPing to events hosted by {event.group.name}.'
    if event.organizer and user_is_banned_by_organizer(user, event.organizer):
        return 'You are banned from RSVPing to events by this organizer.'
    return None


def _promote_waitlisted_if_spot(event):
    if not (event.waitlist_enabled and event.capacity is not None):
        return
    if event.rsvps.filter(status='confirmed').count() >= event.capacity:
        return
    oldest_waitlisted = event.rsvps.filter(status='waitlisted').order_by('timestamp').first()
    if not oldest_waitlisted or not oldest_waitlisted.user:
        return
    oldest_waitlisted.status = 'confirmed'
    oldest_waitlisted.timestamp = timezone.now()
    oldest_waitlisted.save()
    create_notification(
        oldest_waitlisted.user,
        f'You have been moved from the waitlist to confirmed for {event.title}!',
        link=event.get_absolute_url(),
    )


def remove_user_rsvps_for_group(user, group):
    """Remove a banned user's RSVPs for all events in the group."""
    from events.models import Event, RSVP

    removed_titles = []
    for event in Event.objects.filter(group=group):
        try:
            rsvp = RSVP.objects.get(event=event, user=user)
        except RSVP.DoesNotExist:
            continue

        was_confirmed = rsvp.status == 'confirmed'
        removed_titles.append(event.title)

        with transaction.atomic():
            rsvp.delete()
            if was_confirmed:
                _promote_waitlisted_if_spot(event)

    if removed_titles:
        if len(removed_titles) == 1:
            message = f'Your RSVP for "{removed_titles[0]}" was removed because you were banned from {group.name}.'
        else:
            message = (
                f'Your RSVPs for {len(removed_titles)} events were removed because you were banned from {group.name}.'
            )
        create_notification(
            user,
            message,
            link=reverse('group_detail', kwargs={'group_id': group.id}),
        )