from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from blog.models import Post
import random
import string


class BaseTestCase(TestCase):

    def given_author_exists(self, first_name="author", surname="surname",
                            email=None, phone=None):
        author, created = User.objects.get_or_create(first_name=first_name,
                                                surname=surname,
                                                email=email, phone=phone)
        return author
    
    def given_post_exists(self, content="content", title="title", updated_at=datetime.now(),
                          author=None):
        if author is None:
            author = self.given_author_exists()
        post, created = Post.objects.get_or_create(
            content=content, title=title, updated_at=updated_at,
            author=author
        )
        return post


# Create your tests here.
class OurTestCase(BaseTestCase):
    

    def test_index_page_returns_queryset_correctly(self):
        # Arrange
        User = User.objects.create_user("user", password="1234")

        self.client.login(username=User.username, password="1234")


        author = self.given_author_exists()
        author_2 = self.given_author_exists(first_name="new author")

        for i in range(20):
            Post.objects.create(title=random.choice(string.ascii_letters), 
                                       content="".join(random.choice(string.ascii_letters) for i in range(100)), 
                                       author=author,
                                    updated_at=datetime.now())
        
        for i in range(20):
            Post.objects.create(title=random.choice(string.ascii_letters), 
                                       content="".join(random.choice(string.ascii_letters) for i in range(100)), 
                                       author=author_2,
                                    updated_at=datetime.now())
        
        latest_post = self.given_post_exists(updated_at=datetime.now() + timedelta(days=1))

        # Act
        response = self.client.get(reverse('blog:index'))

        # Assert
        self.assertTemplateUsed(response, "blog/index.html")
        self.assertEqual(latest_post, response.context.get("posts")[0])
        self.assertEqual(5, len(response.context.get("posts")))


    def test_index_page_uses_correct_template(self):
        # Arrange
        User = User.objects.create_user("user", password="1234")

        self.client.login(username=User.username, password="1234")


        # Act
        response = self.client.get(reverse('blog:index'))

        # Assert
        self.assertTemplateUsed(response, "blog/index.html")



# test_use_correct_template 
# blog/edit_post.html
# Arrange - make sure we have an existing post
# Act - get edit_post view
# Assert - check template used in respones


# test_edit_post_call_actually_edits_post
# Arrange - make sure we have an existing post
# Act - send data to view/endpoint
# Assert - get post from db, check content was updated