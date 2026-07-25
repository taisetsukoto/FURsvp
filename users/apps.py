from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        from django.db.models.signals import post_delete, post_save
        from users.content_moderation import clear_blocked_terms_cache
        from users.models import BlockedTerm

        def invalidate_blocked_terms_cache(**kwargs):
            clear_blocked_terms_cache()

        post_save.connect(invalidate_blocked_terms_cache, sender=BlockedTerm)
        post_delete.connect(invalidate_blocked_terms_cache, sender=BlockedTerm)
