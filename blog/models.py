from django.db import models

class Author(models.Model):
    first_name = models.CharField(verbose_name="שם", null=False, blank=False)
    surname = models.CharField(verbose_name="משפחה")
    email = models.EmailField(verbose_name="דואר אלקטרוני", null=True, blank=True)
    phone = models.CharField(verbose_name="טלפון", null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.surname}"


class Post(models.Model):
    title = models.CharField(verbose_name="כותרת")
    content = models.TextField(verbose_name="תוכן")
    creation_time = models.DateTimeField(verbose_name=" באמת נוצר בתאריך", null=True)
    updated_at = models.DateTimeField(verbose_name="עדכון אחרון")
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)

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
    author = models.CharField(max_length=100)

    def __str__(self):
        return self.content
