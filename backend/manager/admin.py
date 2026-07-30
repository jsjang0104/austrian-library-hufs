from django.contrib import admin
from .models import Manager

@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ('member', 'manager_type', 'join_date')
    raw_id_fields = ('member',)
    list_filter = ('manager_type',)
    search_fields = ('member__email', 'member__name')
    fields = ('member', 'manager_type', 'manager_last_activity')
    readonly_fields = ('manager_last_activity',)
