from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_inventoryuser_control_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('stock_in', 'Stock In'), ('stock_out', 'Stock Out'), ('procurement_request', 'Procurement Request'), ('inventory_action', 'Inventory Action')], default='inventory_action', max_length=30)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_notifications', to='inventory.inventoryuser')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_inventory_notifications', to='inventory.inventoryuser')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
