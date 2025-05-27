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

import datetime

from colorfield.fields import ColorField
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords

from choices import GenderApproach, ApprovalStatus
from helpers import weekday_translation
from managers import UserManager
from shibutzim import hebrew
from shibutzim.cached_queries import invalidate_cache_configuration
from shibutzim.constants import COLOR_PALETTE, BASIC_URL_FOR_ACTIVITY_IN_POWER_LINK


class User(AbstractUser):
    class Meta:
        verbose_name = "משתמש"
        verbose_name_plural = "משתמשים"

    username = None
    email = models.EmailField(('email address'), unique=True)
    email_verified = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


class Hitagdut(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    monthly_activities_goal_for_member = models.PositiveIntegerField(default=4, null=True, blank=True,
                                                                     verbose_name=hebrew.MONTHLY_ACTIVITIES_GOAL_FOR_MEMBER)
    rakazim = models.ManyToManyField(to="Profile", related_name="hitagduyot_rakaz_of", verbose_name=hebrew.RAKAZIM,
                                     blank=True)
    can_assign_rakazim_to_activities = models.BooleanField(default=False,
                                                           verbose_name=hebrew.CAN_ASSIGN_RAKAZIM_TO_ACTIVITIES)
    need_confirmation_to_signup_to_activities = models.BooleanField(default=False,
                                                                    verbose_name=hebrew.NEED_CONFIRMATION_TO_SIGNUP_TO_ACTIVITIES)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.HITAGDUT
        verbose_name_plural = hebrew.HITAGDUYOUT


class District(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.DISTRICT
        verbose_name_plural = hebrew.DISTRICTS


class MeorerGroup(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    rakaz = models.CharField(max_length=200, blank=True, null=True, verbose_name=hebrew.RAKAZ)
    monthly_goal = models.PositiveIntegerField(blank=True, verbose_name=hebrew.MONTHLY_GOAL)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.MEORER_GROUP
        verbose_name_plural = hebrew.MEORER_GROUPS


class Qualification(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=hebrew.NAME)
    color = ColorField(samples=COLOR_PALETTE, default='#FFFFFF', verbose_name=hebrew.COLOR)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.QUALIFICATION
        verbose_name_plural = hebrew.QUALIFICATIONS


class Content(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    color = ColorField(samples=COLOR_PALETTE, default='#FFFFFF', verbose_name=hebrew.COLOR)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.CONTENT
        verbose_name_plural = hebrew.CONTENTS


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hitagdut = models.ForeignKey(Hitagdut, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=hebrew.HITAGDUT)
    meorer_groups = models.ManyToManyField(MeorerGroup, blank=True, verbose_name=hebrew.MEORER_GROUP,
                                           related_name="profiles")
    phone = PhoneNumberField(blank=True, null=True, verbose_name=hebrew.PHONE)
    gender_approach = models.CharField(choices=GenderApproach.choices, null=True, blank=True,
                                       verbose_name=hebrew.GENDER_APPROACH)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=hebrew.DISTRICT)
    is_driver = models.BooleanField(default=True, verbose_name=hebrew.IS_DRIVER)
    birth_date = models.DateField(null=True, blank=True, verbose_name=hebrew.BIRTH_DATE)
    qualifications = models.ManyToManyField(Qualification, verbose_name=hebrew.QUALIFICATIONS, blank=True,
                                            related_name="profiles")
    my_activities = models.ManyToManyField(to="Activity", through="ProfileActivity", verbose_name=hebrew.ACTIVITIES)
    can_be_rakaz_of_activities = models.BooleanField(default=False, verbose_name=hebrew.CAN_BE_RAKAZ_OF_ACTIVITIES)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def my_age(self):
        today = datetime.datetime.today()
        my_exact_age = relativedelta(today, self.birth_date)
        my_age = f'{my_exact_age.years}.{my_exact_age.months}'
        return my_age

    my_age.fget.short_description = "גיל"

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def email(self):
        return self.user.email

    class Meta:
        verbose_name = hebrew.PROFILE
        verbose_name_plural = hebrew.PROFILE


class ActivityType(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = hebrew.ACTIVITY_TYPE
        verbose_name_plural = hebrew.ACTIVITY_TYPES


class Activity(models.Model):
    name = models.CharField(max_length=200, verbose_name=hebrew.NAME)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name=hebrew.ACTIVITY_TYPE)
    date = models.DateField(verbose_name=hebrew.DATE)
    content = models.ForeignKey(Content, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=hebrew.CONTENT)
    start_hour = models.TimeField(verbose_name=hebrew.START_HOUR)
    end_hour = models.TimeField(verbose_name=hebrew.END_HOUR)
    location = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.LOCATION)
    city = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.CITY)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, blank=True, null=True,
                                 verbose_name=hebrew.DISTRICT)
    topic = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.TOPIC)
    required_qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True, blank=True,
                                               verbose_name=hebrew.REQUIRED_QUALIFICATION)
    audience = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.AUDIENCE)
    members_needed = models.PositiveIntegerField(verbose_name=hebrew.MEMBER_NEEDED)
    contact = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.CONTACT)
    order_number = models.PositiveIntegerField(null=True, blank=True, verbose_name=hebrew.ORDER_NUMBER)
    client_name = models.CharField(max_length=200, null=True, blank=True, verbose_name=hebrew.CLIENT_NAME)
    comments = models.TextField(null=True, blank=True, verbose_name=hebrew.COMMENTS)
    activity_id_in_power_link = models.CharField(unique=True, null=True, blank=True,
                                                 verbose_name=hebrew.ACTIVITY_ID_IN_POWER_LINK)
    is_cancelled = models.BooleanField(default=False, verbose_name=hebrew.IS_CANCELLED)
    red_flag = models.BooleanField(default=False, verbose_name=hebrew.RED_FLAG, help_text=hebrew.RED_FLAG_HELP_TEXT)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name} {self.date.strftime("%d/%m/%Y")}'

    @property
    def weekday_of_activity(self):
        weekday = self.date.strftime('%w')
        return weekday

    @property
    def hebrew_weekday(self):
        weekday = self.date.strftime('%A')
        hebrew_week_day = weekday_translation[weekday]
        return hebrew_week_day

    weekday_of_activity.fget.short_description = "יום בשבוע"
    hebrew_weekday.fget.short_description = "יום בשבוע"

    @property
    def link_to_power_link(self):
        link = f"{BASIC_URL_FOR_ACTIVITY_IN_POWER_LINK}{self.activity_id_in_power_link}"
        return link

    class Meta:
        verbose_name = hebrew.ACTIVITY
        verbose_name_plural = hebrew.ACTIVITIES
        ordering = ['date']


class ProfileActivity(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, verbose_name=hebrew.PROFILE,
                                related_name="activities")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, verbose_name=hebrew.ACTIVITY,
                                 related_name="profiles")
    is_fav = models.BooleanField(default=False, verbose_name=hebrew.IS_FAV)
    is_registered = models.BooleanField(default=False, verbose_name=hebrew.IS_REGISTERED)
    is_rakaz_of_activity = models.BooleanField(default=False, verbose_name=hebrew.IS_RAKAZ_OF_ACTIVITY)
    approval_status = models.CharField(choices=ApprovalStatus.choices, null=True, blank=True,
                                       verbose_name=hebrew.APPROVAL_STATUS)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.profile} {self.activity}'

    class Meta:
        unique_together = [["profile", "activity"]]
        verbose_name = hebrew.PROFILE_ACTIVITY
        verbose_name_plural = hebrew.PROFILE_ACTIVITIES


class Configuration(models.Model):
    key = models.CharField(max_length=200, unique=True, verbose_name=hebrew.KEY)
    value = models.CharField(max_length=200, verbose_name=hebrew.VALUE)
    explanation = models.TextField(verbose_name=hebrew.EXPLANATION, blank=True, null=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = hebrew.CONFIGURATION
        verbose_name_plural = hebrew.CONFIGURATIONS

    def save(
            self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        invalidate_cache_configuration()

    def __str__(self):
        return f'{self.key} {self.value} {self.explanation}'
