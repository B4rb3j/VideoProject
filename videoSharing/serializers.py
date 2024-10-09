from django.utils import timezone
import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Video, Subscription, WatchHistory, Payment, Comment, Rating

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])

        user = User.objects.create(**validated_data)

        Subscription.objects.create(
            user=user,
            subscription_type='free',
            start_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=30)
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'subscription_type', 'subscription_status']


class VideoSerializer(serializers.ModelSerializer):
    average_rating = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    watch_history = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ['id', 'title', 'description', 'upload_date', 'url', 'view_count', 'average_rating', 'is_premium', 'watch_history']

    def get_watch_history(self, obj):
        watch_history = WatchHistory.objects.filter(video=obj)
        return WatchHistorySerializer(watch_history, many=True).data


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['subscription_type', 'is_active', 'start_date', 'end_date']


class WatchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchHistory
        fields = ['user', 'video', 'watch_date']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'user', 'amount', 'transaction_id', 'status', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['user', 'video', 'content', 'created_at']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'user', 'video', 'score', 'created_at']
