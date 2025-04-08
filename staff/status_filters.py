from django import template

register = template.Library()

@register.filter
def status_color(status):
    color_map = {
        "hold": "purple",
        "complete": "green",
        "pending": "red",
        "claim-complete": "skyblue",
        "incomplete": "orange",
    }
    return color_map.get(status.lower().replace(" ", "-"), "black")
