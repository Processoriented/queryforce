from django.contrib import admin
from .models import ForceAPI, Query, DisplayColumn
from .models import Report, ReportQuery, Parameter


class DisplayColumnInline(admin.TabularInline):
    model = DisplayColumn
    extra = 0

class ParameterInline(admin.TabularInline):
    model = Parameter
    extra = 0

class QueryAdmin(admin.ModelAdmin):
    inlines = [DisplayColumnInline, ParameterInline]

class ReportQueryInline(admin.TabularInline):
    model = ReportQuery
    extra = 0

class ReportAdmin(admin.ModelAdmin):
    inlines = [ReportQueryInline]

admin.site.register(ForceAPI)
admin.site.register(Query, QueryAdmin)
admin.site.register(Report, ReportAdmin)
