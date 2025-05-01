from datetime import datetime
from django.shortcuts import render, redirect
from blog.forms import PostForm
from blog.models import Post, Author

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


def add_post(request):
    if request.method == "POST":      
        form = PostForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("blog:index")
    else:
        form = PostForm()
    
    temp_name = "blog/add_post.html"
    return render(request=request, template_name=temp_name, context={
        "form": form
    })