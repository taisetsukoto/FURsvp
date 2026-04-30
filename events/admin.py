from django.contrib import admin
from .models import Country, State, Group, Event, RSVP, Post


class StateInline(admin.TabularInline):
    model = State
    extra = 1
    fields = ('state_code', 'state_name')
    ordering = ('state_name',)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('alpha_2_code', 'alpha_3_code', 'country_name')
    search_fields = ('alpha_2_code', 'alpha_3_code', 'country_name')
    ordering = ('country_name',)
    inlines = (StateInline,)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('state_code', 'state_name', 'country')
    list_filter = ('country',)
    search_fields = ('state_code', 'state_name', 'country__country_name')
    ordering = ('country__alpha_2_code', 'state_name')
    raw_id_fields = ('country',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'contact_email', 'telegram_channel', 'telegram_webhook_channel')
    search_fields = ('name', 'description', 'website', 'contact_email', 'telegram_channel', 'telegram_webhook_channel')
    ordering = ('name',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'date', 'city', 'state', 'country', 'timezone', 'status')
    list_filter = ('status', 'age_restriction', 'country', 'state', 'timezone')
    search_fields = (
        'title', 'description', 'city', 'address',
        'state__state_name', 'country__country_name', 'timezone'
    )
    raw_id_fields = ('group', 'organizer')
    ordering = ('-date', 'start_time')
    list_select_related = ('group', 'state', 'country')
    fieldsets = (
        (None, {
            'fields': ('title', 'group', 'organizer', 'status')
        }),
        ('Location', {
            'fields': ('address', 'city', 'country', 'state', 'timezone')
        }),
        ('Timing & Capacity', {
            'fields': ('date', 'start_time', 'end_time', 'age_restriction', 'capacity', 'waitlist_enabled')
        }),
        ('Visibility & Questions', {
            'fields': (
                'attendee_list_public', 'enable_rsvp_questions',
                'question1_text', 'question2_text', 'question3_text'
            )
        }),
    )


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'name', 'status', 'timestamp')
    list_filter = ('status',)
    search_fields = ('event__title', 'user__username', 'name')
    raw_id_fields = ('event', 'user')
    ordering = ('-timestamp',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'published', 'original_link', 'guid')
    search_fields = ('title', 'content', 'original_link', 'guid')
    ordering = ('-published',)
