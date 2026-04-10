import os, glob, re

replacements = {
    'btn-glass': 'btn btn-secondary',
    'btn-primary-glass': 'btn btn-primary',
    'btn-success-glass': 'btn btn-success',
    'btn-danger-glass': 'btn btn-danger',
    'btn-edit-glass': 'btn btn-secondary',
    'btn-warning-glass': 'btn btn-secondary',
    'glass-card': 'card',
    'glass-form': 'card',
    'glass-table': 'table-wrap',
    'alert-glass': ''
}

count = 0
for filepath in glob.glob('templates/**/*.html', recursive=True):
    if any(x in filepath for x in ['tasks/', 'accounts/', 'finance/', 'files/', 'base.html', 'pagination.html', 'inventory_base.html']):
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        count += 1
        print(f"Updated {filepath}")

print(f"Total files updated: {count}")
