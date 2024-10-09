from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import VideoViewSet, SubscriptionViewSet, WatchHistoryViewSet, RenewSubscriptionView, \
    CancelSubscriptionView, CheckSubscriptionStatusView, UserRegistrationView, PaymentView, PaymentHistoryView, \
    CommentViewSet, RatingViewSet

router = DefaultRouter()
router.register(r'video', VideoViewSet)
router.register(r'subscription', SubscriptionViewSet)
router.register(r'history', WatchHistoryViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'ratings', RatingViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('subscriptions/renew/', RenewSubscriptionView.as_view(), name='renew-subscription'),
    path('subscriptions/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('subscriptions/check/', CheckSubscriptionStatusView.as_view(), name='check-subscription'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('payment/', PaymentView.as_view(), name='payment'),
    path('payment/history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
