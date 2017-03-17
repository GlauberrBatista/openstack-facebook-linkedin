from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from models import ExternalProfile

# We want to display our external profile, not the default user
admin.site.unregister(User)

class ExternalProfileInline(admin.StackedInline):
    model = ExternalProfile

class ExternalProfileAdmin(UserAdmin):
    inlines = [ExternalProfileInline]

admin.site.register(User, ExternalProfileAdmin)
