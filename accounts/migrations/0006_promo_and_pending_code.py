from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_renewal_notif_prefs'),
    ]

    operations = [
        # User.pending_promo_code — promo code saved when user visits /promo/:code before auth
        migrations.AddField(
            model_name='user',
            name='pending_promo_code',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
        # PromoCode model
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('code', models.CharField(db_index=True, max_length=32, unique=True)),
                ('promo_type', models.CharField(
                    choices=[('percent', 'Percent discount'), ('days', 'Bonus days'),
                             ('gift', 'Free gift (activate without purchase)')],
                    default='percent', max_length=16,
                )),
                ('value', models.IntegerField(default=0,
                    help_text='% discount, bonus days, or gift days depending on type')),
                ('description', models.CharField(blank=True, default='', max_length=255)),
                ('plan', models.CharField(blank=True, default='', max_length=20,
                    help_text='Restrict to plan (standard/pro/max), empty = any')),
                ('allowed_periods', models.JSONField(blank=True, default=list,
                    help_text='List of allowed periods (1,3,6,12), empty = any')),
                ('max_uses', models.IntegerField(default=0, help_text='Global usage limit, 0 = unlimited')),
                ('per_user_limit', models.IntegerField(default=1, help_text='Max uses per single user')),
                ('is_active', models.BooleanField(default=True)),
                ('valid_until', models.DateTimeField(blank=True, null=True)),
                ('times_used', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_promos',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        # Subscription.promo_code FK
        migrations.AddField(
            model_name='subscription',
            name='promo_code',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='subscriptions',
                to='accounts.promocode',
            ),
        ),
        # PromoCodeUsage audit log
        migrations.CreateModel(
            name='PromoCodeUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('bonus_days', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('promo', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='usages',
                    to='accounts.promocode',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='promo_usages',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('subscription', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='promo_usages',
                    to='accounts.subscription',
                )),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['promo', 'user'], name='accounts_pr_promo_i_idx')],
            },
        ),
    ]
