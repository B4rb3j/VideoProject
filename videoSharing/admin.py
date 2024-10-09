from django.contrib import admin
from .models import User, Video, Subscription

admin.site.register(User)
admin.site.register(Video)
admin.site.register(Subscription)

