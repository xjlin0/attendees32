from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@stringfilter
@register.simple_tag(takes_context=True)
def convert_urn(context, uri):
    url_converters = {
        'user_organization_name_slug': context['user_organization_name_slug'],
    }
    return uri.format(**url_converters)
