from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from import_export.admin import ImportExportModelAdmin
from .models import Post, Comment

# Register your models here.
@admin.register(Post)
class PostAdmin(ImportExportModelAdmin):
    search_fields = ["title"]
    list_display = ["title", "content", "content_edit", "id", "comment_count", "author", "creation_time", "updated_at"]
    actions = ["clear_comments"]
    list_per_page = 15
    list_filter = ("author", "creation_time")
    date_hierarchy = "creation_time"

    class Media:
        js = ['https://unpkg.com/htmx.org@2.0.4']

    def content_edit(self, obj):
        return obj.content
    
    def comment_count(self, obj):
        return obj.comment_set.count()
        
    @admin.action(description="מחק את התגובות לפוסט")
    def clear_comments(self, request, queryset):
        for post in queryset:
            post.comment_set.all().delete()

@admin.register(Comment)
class CommentAdmin(ImportExportModelAdmin):
    autocomplete_fields = ["post"]
    list_display = ("content", "author", "post", "creation_time")
    list_filter = ("author", "creation_time")
    search_fields = ("content",)
    date_hierarchy = "creation_time"
