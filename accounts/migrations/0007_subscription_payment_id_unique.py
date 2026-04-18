from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    """Prevent duplicate payment processing at the DB level.

    Adds a partial unique index on (payment_method, payment_id) that excludes
    empty payment_id and trial_/gift_ prefixes — those are internal markers,
    not external provider references, and are intentionally repeatable.
    """

    dependencies = [
        ('accounts', '0006_promo_and_pending_code'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='subscription',
            constraint=models.UniqueConstraint(
                fields=['payment_method', 'payment_id'],
                condition=(
                    ~Q(payment_id='')
                    & ~Q(payment_id__startswith='trial_')
                    & ~Q(payment_id__startswith='gift_')
                ),
                name='uniq_subscription_external_payment_id',
            ),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['status', 'expires_at'],
                name='sub_status_expires_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['payment_id'],
                name='sub_payment_id_idx',
            ),
        ),
    ]
