from django import forms

from blog.models import Author, Post

    
class PostForm(forms.ModelForm):
    author = forms.ModelChoiceField(queryset=Author.objects.all(),widget=forms.HiddenInput())
    updated_at = forms.DateTimeField(widget=forms.HiddenInput())
    title = forms.CharField(min_length=10, widget=forms.TextInput(attrs={'class': ['newclas', ''], 'data-name': 'data'}))
    class Meta:
        model = Post
        fields = ['title', 'content', 
                  'author', 'updated_at']