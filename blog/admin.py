from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Author, Post, Comment

# Register your models here.
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "surname", "email", "phone", "post_count"]

    def post_count(self, obj):
        return 0


@admin.register(Post)
class PostAdmin(ImportExportModelAdmin):
    search_fields = ["title"]
    list_display = ["title", "content", "content_edit", "id", "comment_count"]
    actions = ["clear_comments"]
    list_per_page = 15


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
