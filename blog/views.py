from datetime import datetime
from django.db.models import Q
from django.shortcuts import render, redirect
from blog.forms import PostForm
from blog.models import Post, Author

def index(request):
    search = request.GET.get('search')
    posts_queryset = Post.objects.all().order_by("-updated_at")
    if search:
        posts_queryset = posts_queryset.filter(
            Q(title__contains=search) |
            Q(content__contains=search) | Q(author__first_name__contains=search)
        )
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


def _get_author_for_user(user):
    response = Author.objects.get_or_create(first_name=user.username, surname=user.username, email=user.email)
    return response[0]


def add_post(request):
    
    if request.method == "POST":  
        data = request.POST.copy()
        data["updated_at"] = datetime.now()
        data["author"] = _get_author_for_user(request.user)
        form = PostForm(data)

        if form.is_valid():
            form.save()
            return redirect("blog:index")
    else:
        form = PostForm()
    
    temp_name = "blog/add_post.html"
    return render(request=request, template_name=temp_name, context={
        "form": form
    })


def edit_post(request, post_id):
    post = Post.objects.get(id=post_id)
    
    if request.method == "POST":
        post.title = request.POST.get('title')
        post.updated_at = datetime.now()
        post.save()
        return redirect('blog:single_post', post_id=post.id)
    
    temp_name = "blog/edit_post.html"
    context = {
        "post": post
    }
    return render(request=request, template_name=temp_name, context=context)
