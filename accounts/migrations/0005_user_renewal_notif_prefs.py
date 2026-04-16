from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_support_ticket_system'),
    ]

    operations = [
        # User: auto-renewal fields
        migrations.AddField(
            model_name='user',
            name='auto_renew',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='preferred_payment_method',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        migrations.AddField(
            model_name='user',
            name='preferred_crypto_asset',
            field=models.CharField(blank=True, default='USDT', max_length=16),
        ),
        # User: notification preferences
        migrations.AddField(
            model_name='user',
            name='notification_prefs',
            field=models.JSONField(blank=True, default=dict),
        ),
        # Subscription: upgrade tracking
        migrations.AddField(
            model_name='subscription',
            name='upgrade_from',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='upgrades',
                to='accounts.subscription',
            ),
        ),
    ]
