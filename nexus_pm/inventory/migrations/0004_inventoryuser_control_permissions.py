from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_inventoryuser_alter_alert_acknowledged_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_adjustments_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_alerts_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_limits_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_rentals_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_serials_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_access_shortage_page',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_adjustments',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_alerts',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_limits',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_rentals',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_serials',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='inventoryuser',
            name='can_manage_shortage_exports',
            field=models.BooleanField(default=True),
        ),
    ]
