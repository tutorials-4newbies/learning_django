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
import logging
import urllib
from datetime import datetime

import django_filters.rest_framework as filters
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db.models import OuterRef, Count, Subquery, IntegerField, Q, DateField
from django.db.models.functions import ExtractWeekDay, Cast
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_tracking.mixins import LoggingMixin

from choices import ApprovalStatus
from helpers import SubqueryCount
from meorer_api_shibutzim.locator import ServiceLocator
from shibutzim.constants import TOO_LATE_TO_UNREGISTER, MAX_DAYS_BEFORE_ACTIVITY_TO_UNREGISTER, COUNTRY_WIDE
from shibutzim.filters import ActivityAPIFilter
from shibutzim.models import Hitagdut, MeorerGroup, District, Qualification, Content, Profile, \
    Activity, ProfileActivity, ActivityType, Configuration
from shibutzim.permissions import HasValidKaveretHeader
from shibutzim.serializers import HitagdutSerializer, MeorerGroupSerializer, DistrictSerializer, \
    QualificationSerializer, ContentSerializer, ProfileSerializer, ChangeDistrictSerializer, \
    AddOrRemoveMeorerGroupFromProfileSerializer, ActivitySerializer, \
    ProfileActivitySerializer, ActivityFromPowerLinkSerializer, MeProfileSerializer, AddOrRemoveFromActivitySerializer, \
    ActivityTypeSerializer, AllDataSerializer, ActivityDatesSerializer, \
    AddMemberToAllActivitiesWithTheSameOrderSerializer, AddOrRemoveOtherMemberFromActivitySerializer, \
    AddOtherMemberToAllActivitiesWithTheSameOrderSerializer, RequestPasswordResetSerializer, \
    RequestPasswordResetResponseSerializer, PasswordResetSerializer, \
    PasswordResetResponseSerializer, ActivitiesInMembersSerializer

logger = logging.getLogger(__name__)


class AllDataViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=["GET"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AllDataSerializer)
    def get_all_data(self, request, pk=None):
        contents = Content.objects.all().values_list("name", flat=True)
        try:
            message = Configuration.objects.get(key="message").value
        except Configuration.DoesNotExist:
            message = None
        qualifications = Qualification.objects.values("id", "name", "color")
        districts = District.objects.all().values_list("name", flat=True)
        activity_types = ActivityType.objects.all().values_list("name", flat=True)
        data = {"contents": contents, "qualifications": qualifications, "districts": districts,
                "activity_types": activity_types, "message": message}
        serializer = self.get_serializer(data)
        return Response(serializer.data)


class HitagdutViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Hitagdut.objects.all()
    serializer_class = HitagdutSerializer
    permission_classes = [permissions.IsAuthenticated]
    logging_methods = ['POST']


class MeorerGroupViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MeorerGroup.objects.all()
    serializer_class = MeorerGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    logging_methods = ['POST']

    @action(methods=["POST"], detail=True, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveMeorerGroupFromProfileSerializer)
    def add_member_to_meorer_group(self, request, pk=None):
        meorer_group_id = request.data["meorer_group_id"]
        meorer_group = get_object_or_404(MeorerGroup, pk=meorer_group_id)
        profile_id = request.data["profile_id"]
        profile_to_add_to_group = get_object_or_404(Profile, pk=profile_id)
        profile_to_add_to_group.meorer_groups.add(meorer_group)
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=True, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveMeorerGroupFromProfileSerializer)
    def remove_member_from_meorer_group(self, request, pk=None):
        meorer_group_id = request.data["meorer_group_id"]
        meorer_group = get_object_or_404(MeorerGroup, pk=meorer_group_id)
        profile_id = request.data["profile_id"]
        profile_to_remove_from_group = get_object_or_404(Profile, pk=profile_id)
        profile_to_remove_from_group.meorer_groups.remove(meorer_group)
        return Response(status=status.HTTP_201_CREATED)


class DistrictViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [permissions.AllowAny]
    logging_methods = ['POST']


class QualificationViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    permission_classes = [permissions.AllowAny]
    logging_methods = ['POST']


class ContentViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [permissions.AllowAny]
    logging_methods = ['POST']


class ProfileViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    logging_methods = ['POST']

    @action(methods=["GET"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=MeProfileSerializer)
    def home(self, request, pk=None):
        serializer_class = MeProfileSerializer
        profile = request.user.profile
        serializer = serializer_class(profile)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    def add_member_to_activity(self, request, pk=None):
        profile = request.user.profile
        need_approval_to_sign_to_activity = profile.hitagdut.need_confirmation_to_signup_to_activities
        activity = request.data["activity"]
        if not need_approval_to_sign_to_activity:
            log = f"member: {profile} signed to activity:{activity}"
            logger.info(log)
            add_member_to_activity, created = ProfileActivity.objects.get_or_create(profile=profile,
                                                                                    activity_id=activity)
            if created or add_member_to_activity.is_registered is False:
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_with_ics(activity=Activity.objects.get(pk=activity), profile=profile)
                add_member_to_activity.is_registered = True
                add_member_to_activity.save()
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_208_ALREADY_REPORTED)
        else:
            log = f"member: {profile} wants to sign to activity:{activity} and is waiting for approval"
            logger.info(log)
            waiting_for_confirmation, created = ProfileActivity.objects.get_or_create(profile=profile,
                                                                                      activity_id=activity)
            if created:
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_to_inform_need_confirmation_to_signup_to_activities(
                    activity=Activity.objects.get(pk=activity), profile=profile)
                waiting_for_confirmation.approval_status = ApprovalStatus.PENDING
                waiting_for_confirmation.save()
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_208_ALREADY_REPORTED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    # I think we dont need this part, cause i cant sign myself
    def add_rakaz_to_activity(self, request, pk=None):
        profile = request.user.profile
        activity = request.data["activity"]
        log = f"member: {profile} signed to be rakaz of activity:{activity}"
        logger.info(log)
        add_rakaz_to_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity_id=activity)
        if created or add_rakaz_to_activity.is_rakaz_of_activity is False:
            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
            send_mail_service.send_mail_with_ics(activity=Activity.objects.get(pk=activity), profile=profile)
            add_rakaz_to_activity.is_rakaz_of_activity = True
            add_rakaz_to_activity.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_208_ALREADY_REPORTED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveOtherMemberFromActivitySerializer)
    def add_other_member_to_activity(self, request, pk=None):
        logger.info(request.data)
        profile = Profile.objects.get(id=request.data["profile"])
        activity = request.data["activity"]
        log = f"member: {profile} signed to activity:{activity} by {request.user.profile}"
        logger.info(log)

        add_member_to_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity_id=activity)
        if created or add_member_to_activity.is_registered is False:
            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
            send_mail_service.send_mail_with_ics(activity=Activity.objects.get(pk=activity),
                                                 profile=profile)
            add_member_to_activity.is_registered = True
            add_member_to_activity.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_208_ALREADY_REPORTED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveOtherMemberFromActivitySerializer)
    def add_other_rakaz_to_activity(self, request, pk=None):
        logger.info(request.data)
        profile = Profile.objects.get(id=request.data["profile"])
        if profile.can_be_rakaz_of_activities is True:
            activity = request.data["activity"]
            add_rakaz_to_activity, created = ProfileActivity.objects.get_or_create(profile=profile,
                                                                                   activity_id=activity)
            if created or add_rakaz_to_activity.is_rakaz_of_activity is False:
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_with_ics(activity=Activity.objects.get(pk=activity),
                                                     profile=profile)
                add_rakaz_to_activity.is_rakaz_of_activity = True
                add_rakaz_to_activity.save()
                log = f"member: {profile} signed to be rakaz in activity:{activity} by {request.user.profile}"
                logger.info(log)
                return Response(status=status.HTTP_201_CREATED)

            else:
                return Response(status=status.HTTP_208_ALREADY_REPORTED)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    def add_member_to_fav_activity(self, request, pk=None):
        profile = request.user.profile
        activity = request.data["activity"]
        log = f"member: {profile} marked activity:{activity} as fav"
        logger.info(log)
        add_member_fav_to_activity = ProfileActivity.objects.get_or_create(profile=profile, activity_id=activity)
        add_member_fav_to_activity[0].is_fav = True
        add_member_fav_to_activity[0].save()
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    def remove_member_from_activity(self, request, pk=None):
        profile = request.user.profile
        activity = request.data["activity"]
        log = f"member: {profile} remove himself/herself from activity:{activity}"
        logger.info(log)
        remove_member_from_activity = ProfileActivity.objects.get(profile=profile, activity_id=activity)
        today = datetime.today()
        activity_date = Activity.objects.get(id=activity).date
        delta = relativedelta(activity_date, today)
        delta_in_days = (delta.days + delta.months * 30)
        if delta_in_days < MAX_DAYS_BEFORE_ACTIVITY_TO_UNREGISTER:
            return Response(status=status.HTTP_403_FORBIDDEN, data={"message": TOO_LATE_TO_UNREGISTER})
        if remove_member_from_activity.is_fav is False and remove_member_from_activity.is_rakaz_of_activity is False:
            remove_member_from_activity.delete()
        else:
            remove_member_from_activity.is_registered = False
            remove_member_from_activity.save()
        send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
        send_mail_service.send_mail_to_inform_cancellation(activity=Activity.objects.get(pk=activity), profile=profile)
        return Response(status=status.HTTP_201_CREATED)

    # i dont think we need it
    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    def remove_rakaz_from_activity(self, request, pk=None):
        profile = request.user.profile
        activity = request.data["activity"]
        log = f"member: {profile} remove himself/herself from being rakaz activity:{activity}"
        logger.info(log)
        remove_rakaz_from_activity = ProfileActivity.objects.get(profile=profile, activity_id=activity)
        today = datetime.today()
        activity_date = Activity.objects.get(id=activity).date
        delta = relativedelta(activity_date, today)
        delta_in_days = (delta.days + delta.months * 30)
        if delta_in_days < MAX_DAYS_BEFORE_ACTIVITY_TO_UNREGISTER:
            return Response(status=status.HTTP_403_FORBIDDEN, data={"message": TOO_LATE_TO_UNREGISTER})
        if remove_rakaz_from_activity.is_fav is False and remove_rakaz_from_activity.is_registered is False:
            remove_rakaz_from_activity.delete()
        else:
            remove_rakaz_from_activity.is_rakaz_of_activity = False
            remove_rakaz_from_activity.save()
        send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
        send_mail_service.send_mail_to_inform_cancellation(activity=Activity.objects.get(pk=activity),
                                                           profile=profile)
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveOtherMemberFromActivitySerializer)
    def remove_other_member_from_activity(self, request, pk=None):
        profile = request.data["profile"]
        activity = request.data["activity"]
        log = f"member: {profile} removed from activity:{activity} by {request.user.profile}"
        logger.info(log)
        try:
            remove_member_from_activity = get_object_or_404(ProfileActivity, profile=profile, activity_id=activity)
            if remove_member_from_activity.is_fav is False and remove_member_from_activity.is_rakaz_of_activity is False:
                remove_member_from_activity.delete()
            else:
                remove_member_from_activity.is_registered = False
                remove_member_from_activity.save()
            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
            send_mail_service.send_mail_to_inform_cancellation_to_member(activity=Activity.objects.get(pk=activity),
                                                                         profile=Profile.objects.get(pk=profile))
            return Response(status=status.HTTP_201_CREATED)
        except Http404:
            return JsonResponse({'error': 'נראה שהחבר כבר לא רשום לפעילות'}, status=404)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveOtherMemberFromActivitySerializer)
    def remove_other_rakaz_from_activity(self, request, pk=None):
        profile = request.data["profile"]
        activity = request.data["activity"]
        log = f"member: {profile} removed from being rakaz activity:{activity} by {request.user.profile}"
        logger.info(log)
        try:
            remove_rakaz_from_activity = get_object_or_404(ProfileActivity, profile=profile, activity_id=activity)
            if remove_rakaz_from_activity.is_fav is False and remove_rakaz_from_activity.is_registered is False:
                remove_rakaz_from_activity.delete()
            else:
                remove_rakaz_from_activity.is_rakaz_of_activity = False
                remove_rakaz_from_activity.save()
            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
            send_mail_service.send_mail_to_inform_cancellation_to_member(activity=Activity.objects.get(pk=activity),
                                                                         profile=Profile.objects.get(pk=profile))
            return Response(status=status.HTTP_201_CREATED)
        except Http404:
            return JsonResponse({'error': 'נראה שהחבר כבר לא רשום לריכוז הפעילות'}, status=404)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOrRemoveFromActivitySerializer)
    def remove_member_from_fav_activity(self, request, pk=None):
        profile = request.user.profile
        activity = request.data["activity"]
        log = f"member: {profile} removed fav from activity:{activity}"
        logger.info(log)
        remove_member_from_fav_activity = ProfileActivity.objects.get(profile=profile, activity_id=activity)
        if remove_member_from_fav_activity.is_registered is False:
            remove_member_from_fav_activity.delete()
        else:
            remove_member_from_fav_activity.is_fav = False
            remove_member_from_fav_activity.save()

        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=ChangeDistrictSerializer)
    def change_district(self, request, pk=None):
        logger.info(request.data)
        profile = request.user.profile
        district = get_object_or_404(District, pk=request.data["district"])
        profile.district = district
        profile.save()
        return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddMemberToAllActivitiesWithTheSameOrderSerializer)
    def add_member_to_all_activities_with_the_same_order(self, request, pk=None):
        profile = request.user.profile
        need_approval_to_sign_to_activity = profile.hitagdut.need_confirmation_to_signup_to_activities
        order_number = request.data["order_number"]
        activities = Activity.objects.filter(order_number=order_number, is_cancelled=False)
        if not need_approval_to_sign_to_activity:
            log = f"member: {profile} signed to all activities in order number:{order_number}"
            logger.info(log)
            for activity in activities:
                profile_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity=activity)
                if not profile_activity.is_registered:
                    profile_activity.is_registered = True
                    send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                    send_mail_service.send_mail_with_ics(activity=activity, profile=profile)
                    profile_activity.save()

            return Response(status=status.HTTP_201_CREATED,
                            data={"massage": "member added to all activities with the same order number"})
        else:
            log = f"member: {profile} wants to sign to order number:{order_number} and is waiting for approval"
            logger.info(log)
            for activity in activities:
                waiting_for_confirmation, created = ProfileActivity.objects.get_or_create(profile=profile,
                                                                                          activity=activity)
                if created or waiting_for_confirmation.is_registered is False:
                    waiting_for_confirmation.approval_status = ApprovalStatus.PENDING
                    send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                    send_mail_service.send_mail_to_inform_need_confirmation_to_signup_to_activities(
                        activity=activity, profile=profile)
                    waiting_for_confirmation.save()

            return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddMemberToAllActivitiesWithTheSameOrderSerializer)
    def add_rakaz_to_all_activities_with_the_same_order(self, request, pk=None):
        profile = request.user.profile
        order_number = request.data["order_number"]
        log = f"rakaz: {profile} signed to all activities in order number:{order_number}"
        logger.info(log)
        activities = Activity.objects.filter(order_number=order_number, is_cancelled=False)
        for activity in activities:
            profile_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity=activity)
            if not profile_activity.is_rakaz_of_activity:
                profile_activity.is_rakaz_of_activity = True
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_with_ics(activity=activity, profile=profile)
                profile_activity.save()

        return Response(status=status.HTTP_201_CREATED,
                        data={"massage": "rakaz added to all activities with the same order number"})

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOtherMemberToAllActivitiesWithTheSameOrderSerializer)
    def add_other_member_to_all_activities_with_the_same_order(self, request, pk=None):
        logger.info(request.data)
        profile_id = request.data["profile_id"]
        profile = get_object_or_404(Profile, pk=profile_id)
        order_number = request.data["order_number"]
        log = f"member: {profile} was added all activities in order number:{order_number} by {request.user.profile}"
        logger.info(log)
        activities = Activity.objects.filter(order_number=order_number, is_cancelled=False)
        for activity in activities:
            profile_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity=activity)
            if not profile_activity.is_registered:
                profile_activity.is_registered = True
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_with_ics(activity=activity, profile=profile)
                profile_activity.save()

        return Response(status=status.HTTP_201_CREATED,
                        data={"massage": "other member added to all activities with the same order number"})

    @action(methods=["POST"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=AddOtherMemberToAllActivitiesWithTheSameOrderSerializer)
    def add_other_rakaz_to_all_activities_with_the_same_order(self, request, pk=None):
        logger.info(request.data)
        profile_id = request.data["profile_id"]
        profile = get_object_or_404(Profile, pk=profile_id)
        order_number = request.data["order_number"]
        log = f"rakaz: {profile} was added all activities in order number:{order_number} by {request.user.profile}"
        logger.info(log)
        activities = Activity.objects.filter(order_number=order_number, is_cancelled=False)
        for activity in activities:
            profile_activity, created = ProfileActivity.objects.get_or_create(profile=profile, activity=activity)
            if not profile_activity.is_rakaz_of_activity:
                profile_activity.is_rakaz_of_activity = True
                send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
                send_mail_service.send_mail_with_ics(activity=activity, profile=profile)
                profile_activity.save()

        return Response(status=status.HTTP_201_CREATED,
                        data={"massage": "other rakaz added to all activities with the same order number"})

    @action(methods=["GET"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=ActivitiesInMembersSerializer)
    def members_in_my_responsibility(self, request, pk=None):
        logger.info(request.data)
        my_hitagduts = Hitagdut.objects.filter(rakazim__user=request.user.pk)
        members_in_my_responsibility = Profile.objects.filter(hitagdut__in=my_hitagduts).order_by('user__first_name')
        serializer = self.get_serializer(members_in_my_responsibility, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(methods=["GET"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=ActivitiesInMembersSerializer)
    def rakazim_in_my_responsibility(self, request, pk=None):
        logger.info(request.data)
        profile = request.user.profile
        rakazim_in_my_responsibility = Profile.objects.filter(hitagdut=profile.hitagdut.pk).order_by(
            'user__first_name')
        serializer = self.get_serializer(rakazim_in_my_responsibility, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @extend_schema(request=RequestPasswordResetSerializer, responses=RequestPasswordResetResponseSerializer)
    @action(detail=False, methods=["POST"], permission_classes=(permissions.AllowAny,))
    def request_password_reset(self, request):
        logger.info(request.data)
        email = request.data["email"]
        try:
            user = get_user_model().objects.get(email__iexact=email)
            token = urllib.parse.quote_plus(PasswordResetTokenGenerator().make_token(user))
        except get_user_model().DoesNotExist:
            serializer = RequestPasswordResetResponseSerializer(instance={"reset_requested": True})
            # The rationale for this is that we don't want different behavior exposing for frontend if the user exists or not
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")

        try:
            send_mail_service.notify_reset_password_request(recipient=email, token=token)
            serializer = RequestPasswordResetResponseSerializer(instance={"reset_requested": True})

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception:
            serializer = RequestPasswordResetResponseSerializer(instance={"reset_requested": False})
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=PasswordResetSerializer, responses=PasswordResetResponseSerializer)
    @action(detail=False, methods=["POST"], permission_classes=(permissions.AllowAny,))
    def reset_password(self, request):
        email = request.data["email"]
        password = request.data["password"]
        token = request.data["token"]
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            serializer = PasswordResetResponseSerializer(instance={"password_reset": False})
            return Response(serializer.data, status=status.HTTP_200_OK)

        res = PasswordResetTokenGenerator().check_token(user=user, token=token)

        if res:
            user.set_password(password)
            user.save()
            serializer = PasswordResetResponseSerializer(instance={"password_reset": True})

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            serializer = PasswordResetResponseSerializer(instance={"password_reset": False})

            return Response(serializer.data, status=status.HTTP_200_OK)


class ActivityViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = Activity.objects.all().order_by("date").select_related("activity_type", "district")
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ActivityAPIFilter
    logging_methods = ['POST']

    def get_annotate_queryset(self, activities):
        members_signed_to_activity = ProfileActivity.objects.filter(is_registered=True, activity=OuterRef("id"))
        order_and_type_subquery = Activity.objects.filter(order_number=OuterRef("order_number"),
                                                          activity_type=OuterRef("activity_type"),
                                                          is_cancelled=False,
                                                          date__gte=timezone.now()).values(
            "order_number",
            "activity_type").annotate(
            order_and_type_count=Count("id")).values("order_and_type_count")
        annotated_activities = activities.annotate(members_signed_to_activity=SubqueryCount(members_signed_to_activity),
                                                   weekday=ExtractWeekDay("date") - 1,
                                                   activities_with_same_order_number=Subquery(order_and_type_subquery,
                                                                                              output_field=IntegerField())
                                                   )

        return annotated_activities

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user.profile
        user_qualifications = user.qualifications.values_list('id', flat=True)
        user_district = user.district
        qs = qs.filter(Q(required_qualification__in=user_qualifications) | Q(required_qualification=None))
        if District.objects.filter(name=COUNTRY_WIDE).exists():
            if user_district.name != COUNTRY_WIDE:
                country_wide = District.objects.get(name=COUNTRY_WIDE)
                qs = qs.filter(Q(district=user_district) | Q(district=country_wide))
        else:
            qs = qs.filter(district=user_district)
        qs = qs.filter(date__gte=timezone.now(), is_cancelled=False)
        return self.get_annotate_queryset(qs)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader],
            serializer_class=ActivityFromPowerLinkSerializer)
    def add_new_activity(self, request, pk=None):
        logger.info(request.data)
        logger.info(request.headers)
        if Activity.objects.filter(activity_id_in_power_link=request.data["activityid"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity already exists")
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(status=status.HTTP_201_CREATED)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader],
            serializer_class=ActivityFromPowerLinkSerializer)
    def edit_activity(self, request, pk=None):
        logger.info(request.data)
        if not Activity.objects.filter(activity_id_in_power_link=request.data["activityid"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity doesnt exists")
        else:
            instance = Activity.objects.get(activity_id_in_power_link=request.data["activityid"])
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}
            return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader])
    def update_contact(self, request, pk=None):
        logger.info(request.data)
        if not Activity.objects.filter(order_number=request.data["order_number"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity doesnt exists")
        else:

            Activity.objects.filter(order_number=request.data["order_number"]).update(contact=request.data["contact"])

            return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader])
    def update_different_city(self, request, pk=None):
        logger.info(request.data)
        if not Activity.objects.filter(order_number=request.data["order_number"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity doesnt exists")
        else:
            Activity.objects.filter(order_number=request.data["order_number"]).update(
                city=request.data['different_city'])

            return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader],
            serializer_class=ActivityFromPowerLinkSerializer)
    def cancel_activity(self, request, pk=None):
        logger.info(request.data)
        if not Activity.objects.filter(activity_id_in_power_link=request.data["activityid"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity doesnt exists")
        else:
            activity = Activity.objects.get(activity_id_in_power_link=request.data["activityid"])
            activity.is_cancelled = True
            activity.save()

            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")

            activities_with_profiles = ProfileActivity.objects.filter(activity=activity)
            for activity_with_profiles in activities_with_profiles:
                send_mail_service.send_mail_to_inform_cancellation_to_member(activity=activity,
                                                                             profile=activity_with_profiles.profile)
                if activity_with_profiles.is_fav is False:
                    activity_with_profiles.delete()
                else:
                    activity_with_profiles.is_registered = False
                    activity_with_profiles.save()

            return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, permission_classes=[HasValidKaveretHeader],
            serializer_class=ActivityFromPowerLinkSerializer)
    def change_date_of_activity(self, request, pk=None):
        logger.info(request.data)
        if not Activity.objects.filter(activity_id_in_power_link=request.data["activityid"]).exists():
            return Response(status=status.HTTP_200_OK, data="activity doesnt exists")
        else:
            activity = Activity.objects.get(activity_id_in_power_link=request.data["activityid"])
            old_date = activity.date
            fix_old_date = old_date.strftime("%Y-%m-%d")
            new_date = request.data["date"]
            # new date comes in format "dd/mm/yyyy hh:mm
            fix_new_date = datetime.strptime(new_date, "%d/%m/%Y %H:%M")
            fix_new_date = fix_new_date.strftime("%Y-%m-%d")
            send_mail_service = ServiceLocator.get_service("SEND_MAIL_SERVICE")
            activities_with_profiles = ProfileActivity.objects.filter(activity=activity)
            if fix_old_date == fix_new_date:
                new_hour = datetime.strptime(new_date, "%d/%m/%Y %H:%M")
                new_hour = new_hour.strftime("%H:%M")
                activity.start_hour = new_hour
                activity.save()
                for activity_with_profiles in activities_with_profiles:
                    send_mail_service.send_mail_to_inform_change_in_hour_of_activity(activity=activity,
                                                                                     profile=activity_with_profiles.profile,
                                                                                     new_hour=new_hour)
                return Response(status=status.HTTP_200_OK, data="only the time has changed")
            else:

                for activity_with_profiles in activities_with_profiles:
                    send_mail_service.send_mail_to_inform_change_in_date_of_activity(activity=activity,
                                                                                     profile=activity_with_profiles.profile,
                                                                                     new_date=new_date)
                    if activity_with_profiles.is_fav is False:
                        activity_with_profiles.delete()
                    else:
                        activity_with_profiles.is_registered = False
                        activity_with_profiles.save()
                activity.date = fix_new_date
                activity.save()
                return Response(status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, permission_classes=[permissions.IsAuthenticated],
            serializer_class=ActivityDatesSerializer)
    def activities_dates(self, request, pk=None):
        qs = self.get_queryset()
        qs = qs.annotate(date_only=Cast('date', DateField()))
        dates_with_activities = qs.values_list("date_only", flat=True).distinct()
        dates_with_activities_list = list(dates_with_activities)
        data = {"dates": dates_with_activities_list}
        serializer = self.get_serializer(data)
        return Response(serializer.data)

    @action(methods=["GET"], detail=True, permission_classes=[permissions.IsAuthenticated],
            serializer_class=ActivitySerializer)
    def connected_activities(self, request, pk=None):
        prime_activity = Activity.objects.get(pk=pk)
        order_number = prime_activity.order_number
        activity_type_name = prime_activity.activity_type
        connected_activities = self.get_queryset().filter(
            order_number=order_number, activity_type__name=activity_type_name, date__gte=timezone.now())
        serializer = ActivitySerializer(connected_activities, many=True)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class ProfileActivityViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ProfileActivity.objects.all()
    serializer_class = ProfileActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    logging_methods = ['POST']


class ActivityTypeViewSet(LoggingMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ActivityType.objects.all()
    serializer_class = ActivityTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    logging_methods = ['POST']
