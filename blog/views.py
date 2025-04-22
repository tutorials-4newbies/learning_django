from django.shortcuts import render

def index(request):
    context = {}
    temp_name = "blog/index.html"
    return render(request=request, template_name=temp_name, context=context)
