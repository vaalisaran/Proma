from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_inventorynotification_target_url'),
        ('procurement', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='procurementrequest',
            name='decision_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='procurementrequest',
            name='decided_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='procurementrequest',
            name='decided_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decided_procurement_requests', to='inventory.inventoryuser'),
        ),
        migrations.AddField(
            model_name='procurementrequest',
            name='fulfilled_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
