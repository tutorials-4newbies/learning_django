from django.contrib import admin

from .models import Post, Author


class AuthorAdmin(admin.ModelAdmin):
    list_display = ["full_name", "id", "first_name", "surname", "email", "phone"]

    def full_name(self, obj):
        return f"{obj}"

admin.site.register(Author, AuthorAdmin)
admin.site.register(Post)
