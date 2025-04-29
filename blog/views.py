from django.shortcuts import render
from blog.models import Post

def index(request):
    posts_queryset = Post.objects.all().order_by("-updated_at") # QuerySet
    context = {
        "posts": posts_queryset[:5],
        "title": "PAGE TITLE"
    }
    temp_name = "blog/index.html"
    return render(request=request, template_name=temp_name, context=context)


def single_post(request, post_id):
    post = Post.objects.get(id=post_id)
    temp_name = "blog/single_post.html"
    context = {
        "post": post
    }
    return render(request=request, template_name=temp_name, context=context)
