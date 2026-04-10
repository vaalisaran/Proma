from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_inventorynotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventorynotification',
            name='target_url',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
    ]
