from django.contrib import admin
from .models import Author, Post

# Register your models here.
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "surname", "email", "phone", "post_count"]

    def post_count(self, obj):
        return 0


admin.site.register(Post)