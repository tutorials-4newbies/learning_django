from django.db import models

class Author(models.Model):
    first_name = models.CharField(verbose_name="שם", blank=False, null=False)
    surname = models.CharField(verbose_name="משפחה", blank=False, null=False)
    email = models.EmailField(verbose_name="דואר אלקטרוני", blank=True, null=True)
    phone = models.CharField(verbose_name="טלפון", blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.surname}"


class Post(models.Model):
    title = models.CharField(verbose_name="כותרת", blank=False, null=False)
    content = models.TextField(verbose_name="תוכן", blank=False, null=False)
    updated_at = models.DateTimeField(verbose_name="עדכון אחרון", blank=False, null=False)
    author = models.ForeignKey(to=Author, on_delete=models.CASCADE)




