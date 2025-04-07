from django.shortcuts import render

from blog.models import Post, Author


def index(request):
     authors = Author.objects.all()
     posts = Post.objects.all()
     query_params = request.GET
     author_id = query_params.get("author_id")
     if author_id:
          posts = posts.filter(author_id=author_id)
     context = {"posts": posts, "authors": authors}
     return render(request, "blog/index.html", context)


def single_post(request, post_id):
     post = Post.objects.get(pk=post_id)
     context = {"post": post}
     return render(request, "blog/single-post.html", context)