from django.contrib import admin
from django.core.exceptions import ValidationError
from .models import *
from .services import validate_question
class OptionInline(admin.TabularInline): model=Option; extra=4; min_num=2
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin): list_display=("code","title","default_pass_mark","active"); search_fields=("code","title")
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin): list_display=("code","title","module"); list_filter=("module",); search_fields=("code","title")
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display=("code","module","category","question_type","difficulty","status","version","updated_at")
    list_filter=("module","category","question_type","difficulty","status"); search_fields=("code","stem"); inlines=[OptionInline]
    readonly_fields=("image_sha256","created_at","updated_at"); fieldsets=((None,{"fields":("code","module","category","question_type","stem","explanation")}), ("Assessment",{"fields":("marks","difficulty","status","version")}), ("Image",{"fields":("image","image_alt_text","image_sha256")}), ("Audit",{"fields":("created_by","created_at","updated_at")}))
    def save_model(self,request,obj,form,change):
        if not obj.created_by_id: obj.created_by=request.user
        super().save_model(request,obj,form,change)
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin): list_display=("code","title","module","duration_minutes","question_count","pass_mark","max_attempts","status"); list_filter=("module","status"); search_fields=("code","title")
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin): list_display=("candidate","exam","extra_time_minutes","active","assigned_at"); list_filter=("exam","active"); search_fields=("candidate__username","candidate__first_name","candidate__last_name")
@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display=("exam","candidate","attempt_number","status","percentage","passed","started_at","submitted_at"); list_filter=("exam","status","passed"); search_fields=("candidate__username","candidate__first_name","candidate__last_name"); readonly_fields=[f.name for f in Attempt._meta.fields]
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
@admin.register(AuditEvent)
class AuditAdmin(admin.ModelAdmin):
    list_display=("at","actor","action","object_type","object_id","event_hash"); list_filter=("action","object_type"); search_fields=("object_id","event_hash"); readonly_fields=[f.name for f in AuditEvent._meta.fields]
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
admin.site.site_header="Africa Drone Kings Examination Administration"
admin.site.site_title="Africa Drone Kings"
