from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_profile_can_post_blog'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Has the user verified their email?'),
        ),
        migrations.AddField(
            model_name='profile',
            name='verification_token',
            field=models.CharField(blank=True, help_text='Email verification token', max_length=64, null=True),
        ),
    ]
