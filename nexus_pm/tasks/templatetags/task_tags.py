from django import template

register = template.Library()


@register.filter
def getitem(dictionary, key):
    """Get item from dict by key in templates: {{ my_dict|getitem:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.simple_tag
def task_count_for_status(kanban, status):
    """Return count of tasks for a given status in kanban dict."""
    tasks = kanban.get(status, [])
    return len(tasks) if tasks else 0
