from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User
from events.models import Event, Group
from users.models import Profile, GroupDelegation, GroupRole, BlockedTerm
from users.content_moderation import validate_user_display_text
from two_factor.forms import TOTPDeviceForm as BaseTOTPDeviceForm
from turnstile.fields import TurnstileField
import base64


class ModeratedProfileFieldsMixin:
    moderated_profile_fields = ('display_name', 'discord_username', 'telegram_username')

    def clean_display_name(self):
        value = self.cleaned_data.get('display_name')
        validate_user_display_text(value)
        return value

    def clean_discord_username(self):
        value = self.cleaned_data.get('discord_username')
        validate_user_display_text(value)
        return value

    def clean_telegram_username(self):
        value = self.cleaned_data.get('telegram_username')
        validate_user_display_text(value)
        return value


class TurnstileMixin:
    def __init__(self, *args, remote_ip=None, **kwargs):
        super().__init__(*args, **kwargs)
        if 'turnstile' not in self.fields:
            self.fields['turnstile'] = TurnstileField()
        if remote_ip:
            self.fields['turnstile'].remote_ip = remote_ip


class UserRegisterForm(TurnstileMixin, UserCreationForm):
    def clean_username(self):
        username = super().clean_username()
        validate_user_display_text(username)
        return username

    eula_agreement = forms.BooleanField(
        required=True,
        label="I agree to the End User License Agreement (EULA)",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_eula_agreement'
        }),
        error_messages={
            'required': 'You must agree to the End User License Agreement to create an account.'
        }
    )
    
    class Meta:
        model = User
        fields = ['username', 'email']

class UserProfileForm(ModeratedProfileFieldsMixin, forms.ModelForm):
    admin_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Groups"
    )
    clear_profile_picture = forms.BooleanField(required=False, label="Remove Profile Picture")
    can_post_blog = forms.BooleanField(required=False, label="Can post blog posts to Bluesky")

    class Meta:
        model = Profile
        fields = ['display_name', 'profile_picture_base64', 'discord_username', 'telegram_username', 'can_post_blog']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your display name',
            }),
            'discord_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your Discord username',
            }),
            'telegram_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your Telegram username',
            }),
            'profile_picture_base64': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['admin_groups'].initial = Group.objects.filter(group_roles__user=self.instance.user)
        if self.instance and self.instance.profile_picture_base64:
            self.initial['profile_picture_base64'] = self.instance.profile_picture_base64
        # Only show can_post_blog to superusers
        if not (self.instance and self.instance.user and self.instance.user.is_superuser):
            self.fields.pop('can_post_blog', None)

    def _should_update_groups(self):
        prefix = f'{self.prefix}-' if self.prefix else ''
        return self.data.get(f'{prefix}update_groups') == '1'

    def save(self, commit=True):
        instance = super().save(commit=commit)
        user = instance.user
        if not user or not self._should_update_groups():
            return instance

        selected_groups = self.cleaned_data.get('admin_groups', Group.objects.none())
        for group in selected_groups:
            GroupRole.objects.get_or_create(user=user, group=group)
        GroupRole.objects.filter(user=user).exclude(group__in=selected_groups).delete()
        return instance

class UserPublicProfileForm(ModeratedProfileFieldsMixin, forms.ModelForm):
    clear_profile_picture = forms.BooleanField(required=False, label="Remove Profile Picture")
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'you@example.com'
    }))

    class Meta:
        model = Profile
        fields = ['display_name', 'discord_username', 'telegram_username', 'profile_picture_base64']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your display name',
            }),
            'discord_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'username',
            }),
            'telegram_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@username',
            }),
            'profile_picture_base64': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.profile_picture_base64:
            self.initial['profile_picture_base64'] = self.instance.profile_picture_base64
        if self.instance and self.instance.user:
            self.initial['email'] = self.instance.user.email

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            if 'email' in self.cleaned_data:
                instance.user.email = self.cleaned_data['email']
                instance.user.save(update_fields=['email'])
        return instance

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

class RenameGroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

class AssistantAssignmentForm(forms.ModelForm):
    delegated_user = forms.ModelChoiceField(queryset=User.objects.filter(is_superuser=False).exclude(id=None), label="Assign User as Assistant")
    group = forms.ModelChoiceField(queryset=Group.objects.all(), label="For Group")

    class Meta:
        model = GroupDelegation
        fields = ['delegated_user', 'group']

    def __init__(self, *args, **kwargs):
        organizer_profile = kwargs.pop('organizer_profile', None)
        super().__init__(*args, **kwargs)
        if organizer_profile and organizer_profile.user:
            self.fields['group'].queryset = Group.objects.filter(group_roles__user=organizer_profile.user).distinct()
        if organizer_profile and organizer_profile.user:
            self.fields['delegated_user'].queryset = self.fields['delegated_user'].queryset.exclude(id=organizer_profile.user.id)

class UserPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'

class GroupRoleForm(forms.ModelForm):
    class Meta:
        model = GroupRole
        fields = ['user', 'custom_label', 'can_post', 'can_manage_leadership']

    def clean_custom_label(self):
        value = self.cleaned_data.get('custom_label')
        validate_user_display_text(value)
        return value

class TOTPDeviceForm(BaseTOTPDeviceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['token'].label = 'Verification code'
        self.fields['token'].widget.attrs.update({
            'class': 'form-control form-control--otp',
            'placeholder': '000000',
            'maxlength': '6',
        }) 

class BlueskyBlogPostForm(forms.Form):
    title = forms.CharField(max_length=300, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Title'}))
    content = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your blog post here...', 'rows': 6}))


class TurnstileVerificationForm(TurnstileMixin, forms.Form):
    pass


class PasswordResetFormWithTurnstile(TurnstileMixin, PasswordResetForm):
    pass


class BlockedTermForm(forms.ModelForm):
    class Meta:
        model = BlockedTerm
        fields = ['term', 'match_mode', 'notes']
        widgets = {
            'term': forms.TextInput(attrs={
                'class': 'form-control admin-input',
                'placeholder': 'e.g. impostor_admin',
            }),
            'match_mode': forms.Select(attrs={'class': 'form-select admin-select'}),
            'notes': forms.TextInput(attrs={
                'class': 'form-control admin-input',
                'placeholder': 'Optional note',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['match_mode'].initial = BlockedTerm.MATCH_EXACT

    def clean_term(self):
        term = self.cleaned_data.get('term', '').strip().lower()
        if not term:
            raise forms.ValidationError('Term is required.')
        duplicate_qs = BlockedTerm.objects.filter(term__iexact=term)
        if self.instance.pk:
            duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
        if duplicate_qs.exists():
            raise forms.ValidationError('This term is already in the blocked list.')
        return term
