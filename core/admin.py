# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import UserRepo, Issue, IssueLabel, Region, RegionAdmin, LanguageKnowledgeBase, ExperienceNeededKnowledgeBase, TechStackKnowledgeBase
from django.contrib.auth.models import *


class UserRepoAdmin(admin.ModelAdmin):
    """Used to alter `UserRepo` admin site."""
    fieldsets = (
        (None, {
            'fields': ('user', 'repo', 'regions')
        }),
    )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Only show regions related to logged in user when filling `userrepo` form"""
        if db_field.name == "regions":
            kwargs["queryset"] = Region.objects.filter(regionadmin=request.user)
        return super(UserRepoAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def save_form(self, request, form, change):
        """Automatically fills author by extracting it from currunt login user."""
        obj = super( UserRepoAdmin, self).save_form(request, form, change)
        if not change:
            obj.author = request.user
        return obj

    def get_queryset(self, request):
        """Only let the user view their own `UserRepos`."""
        qs = super(UserRepoAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)

    def save_model(self, request, obj, form, change):
        """Save Model"""
        obj.author = request.user
        super(UserRepoAdmin, self).save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Only give the user permissions to modify their own `UserRepos`."""
        if not obj:
            return True
        return obj.author == request.user or request.user.is_superuser


# Re-register UserAdmin
admin.site.register(User, UserAdmin)
admin.site.register(RegionAdmin)

admin.site.register(UserRepo, UserRepoAdmin)
admin.site.register(Region)
admin.site.register(Issue)
admin.site.register(ExperienceNeededKnowledgeBase)
admin.site.register(TechStackKnowledgeBase)
admin.site.register(LanguageKnowledgeBase)
