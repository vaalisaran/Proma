from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.name

    @staticmethod
    def create_default_categories():
        default_categories = [
            "Consumer Electronics",
            "Home Entertainment",
            "Audio Equipment",
            "Cameras & Photography",
            "Smart Home Devices",
            "Gaming Devices",
            "Computer Accessories & Peripherals",
            "Electronic Components",
            "Power & Charging Devices",
        ]
        for cat in default_categories:
            Category.objects.get_or_create(name=cat)

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    serial_number = models.CharField(max_length=100, unique=True, db_index=True, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    datasheet = models.FileField(upload_to='product_datasheets/', blank=True, null=True)
    rack_number = models.CharField(max_length=50, blank=True, null=True)
    shelf_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name
