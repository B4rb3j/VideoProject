import datetime

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=120, null=True, blank=True, unique=True)
    email = models.EmailField(unique=True, null=True)
    password = models.CharField(max_length=120, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    REQUIRED_FIELDS = ['email']
    USERNAME_FIELD = 'username'

    def __str__(self):
        return self.email


class Video(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    upload_date = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    view_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    is_premium = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def allowed_to_watch(self, user):
        if self.is_premium is False:
            return True
        elif self.is_premium and user.subscription.subscription_type == 'premium':
            return True
        else:
            return False


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    subscription_type = models.CharField(max_length=30, choices=[
        ('free', 'Free'),
        ('premium', 'Premium')
    ], default='free')

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = timezone.now() + datetime.timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Subscription of {self.user.email} - Active: {self.is_active}'

    def renew_subscription(self):
        if not self.is_active:
            raise ValueError("Cannot renew an inactive subscription.")
        self.end_date += datetime.timedelta(days=30)
        self.is_active = True
        self.save()

    def cancel_subscription(self):
        self.is_active = False
        self.save()

    def check_subscription_status(self):
        if timezone.now() > self.end_date:
            self.is_active = False
            self.save()


class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    watch_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} watched {self.video.title} on {self.watch_date}'


class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey('Video', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.video.title}'


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    video = models.ForeignKey('Video', on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=2, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Rating by {self.user.username} on {self.video.title} - Score: {self.score}'
