import os, glob

folders = ['inventory', 'products', 'stock', 'reports', 'audit', 'procurement', 'dashboard']

for folder in folders:
    file_path = f"{folder}/models.py"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
            
        content = content.replace('models.ForeignKey(User,', "models.ForeignKey('inventory.InventoryUser',")
        content = content.replace('models.ForeignKey(settings.AUTH_USER_MODEL,', "models.ForeignKey('inventory.InventoryUser',")
        
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated {file_path}")
