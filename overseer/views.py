from django.shortcuts import render
from django.contrib.sites.models import Site
from django.conf import settings

def index(request):
    context = {'api_url': "{protocol}://{domain}/".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                         'domain': Site.objects.get_current().domain})}
    return render(request, 'overseer/index.html', context=context)

def quote(request):
    context = {'api_url': "{protocol}://{domain}/".format(**{'protocol': settings.CURRENT_PROTOCOL,
                                                         'domain': Site.objects.get_current().domain})}
    return render(request, 'overseer/quote.html', context=context)