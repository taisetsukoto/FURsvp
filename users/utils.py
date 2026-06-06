from users.models import Notification
from django.contrib.auth.models import User


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def create_notification(user, message, link=None, event_name=None):
    """
    Creates a new notification for the specified user.
    """
    Notification.objects.create(user=user, message=message, link=link, event_name=event_name)

def approve_all_logged_in_users():
    from users.models import Profile
    users = User.objects.exclude(last_login=None)
    for user in users:
        if hasattr(user, 'profile') and not user.profile.is_verified:
            user.profile.is_verified = True
            user.profile.save()