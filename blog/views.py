from datetime import datetime
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from blog.forms import PostForm, CustomUserCreationForm, CommentForm
from blog.models import Post, Comment
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

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


@csrf_exempt
def edit_post_title(request, post_id):
    post = Post.objects.get(id=post_id)
    post.title = request.POST.get("post-title")
    post.updated_at = timezone.now()
    post.save()
    return HttpResponse(f"""
    <div class="post-item" id="post-{post.id}" hx-swap-oob="true">
      <a
        id="post-title-link-{post.id}"
        href="{reverse('blog:single_post', args=[post.id])}"
      >
        <h2>{ post.title }</h2>
      </a>
      <input
        id="post-title-input-{post.id}"
        type="text"
        name="post-title"
        value="{ post.title }"
        hidden
      />
      <button
        id="post-title-submit-{post.id}"
        hx-post="{reverse('blog:edit_post_title', args=[post.id])}"
        hx-swap="none"
        hidden
        hx-include="previous #post-title-input-{post.id}"
      >
        SUBMIT
      </button>
      <button
        onclick="document.getElementById('post-title-link-{post.id}').hidden = true;
        document.getElementById('post-title-input-{post.id}').hidden = false;
        document.getElementById('post-title-submit-{post.id}').hidden = false;
        this.hidden = true;"
      >
        <i class="fas fa-pencil-alt"></i>
      </button>
      <p>{ post.shortened_content }</p>
      <p>{ post.updated_at }</p>
    </div>
""")

@user_passes_test(lambda u: u.is_anonymous)
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('blog:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@user_passes_test(lambda u: u.is_anonymous)
def login_view(request):
    if request.user.is_authenticated:
        return redirect('blog:index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful!')
                next_page = request.GET.get('next', 'blog:index')
                return redirect(next_page)
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('blog:login')