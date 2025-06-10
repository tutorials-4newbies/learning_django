from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class Post(models.Model):
    title = models.CharField(verbose_name="כותרת")
    content = models.TextField(verbose_name="תוכן")
    creation_time = models.DateTimeField(verbose_name=" באמת נוצר בתאריך", null=True)
    updated_at = models.DateTimeField(verbose_name="עדכון אחרון")
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.title} מאת {self.author}"
    
    @property
    def shortened_content(self):
        return self.content[:30] + "..."
    

class Comment(models.Model):
    content = models.TextField(verbose_name="תוכן ההודעה")
    creation_time = models.DateTimeField(verbose_name=" באמת נוצר בתאריך", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="עדכון אחרון", auto_now=True)
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.content
