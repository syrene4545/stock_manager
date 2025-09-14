from django.contrib import admin
from .models import Purchase, AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id', 'description')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('description', 'user__username')

admin.site.register(Purchase)

    # ✅ Allow editing movement_type directly in the list view





# Register your models here.
