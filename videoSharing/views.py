import datetime

from django.utils import timezone


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .payment_processor import PaymentProcessor
from .models import Video, Subscription, WatchHistory, Payment, Comment, Rating, User
from .serializers import VideoSerializer, SubscriptionSerializer, WatchHistorySerializer, RegisterSerializer, \
    PaymentSerializer, CommentSerializer, RatingSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny


class UserRegistrationView(APIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.user.is_authenticated:
            WatchHistory.objects.update_or_create(
                user=request.user,
                video=instance,
                defaults={'watch_date': timezone.now()}
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]


class WatchHistoryViewSet(viewsets.ModelViewSet):
    queryset = WatchHistory.objects.all()
    serializer_class = WatchHistorySerializer
    permission_classes = [AllowAny]


class RenewSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()

        if not subscription:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)

        amount = request.data.get('amount')

        payment_processor = PaymentProcessor()
        payment_successful = payment_processor.create_payment(request.user, amount)

        if payment_successful:
            payment = Payment.objects.create(
                user=request.user,
                amount=amount,
                transaction_id='some_unique_id',
                status='successful',
                created_at=timezone.now()
            )

            subscription.renew_subscription()
            return Response({"detail": "Subscription renewed successfully."}, status=status.HTTP_200_OK)

        return Response({"detail": "Payment failed."}, status=status.HTTP_402_PAYMENT_REQUIRED)


class CheckSubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(user=request.user)
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response({'error': 'Subscription not found.'}, status=status.HTTP_404_NOT_FOUND)


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = Subscription.objects.filter(user=request.user, is_active=True).first()
        if not subscription:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)

        subscription.cancel_subscription()
        return Response({"detail": "Subscription cancelled successfully."}, status=status.HTTP_200_OK)


class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')

        payment_processor = PaymentProcessor()
        payment_successful = payment_processor.create_payment(request.user, amount)

        if payment_successful:
            try:
                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction_id='some_unique_id',
                    status='successful',
                    created_at=timezone.now()
                )

                subscription = Subscription.objects.get(user=request.user)

                if subscription.subscription_type == 'free':
                    subscription.subscription_type = 'premium'
                    subscription.start_date = timezone.now()
                    subscription.end_date = timezone.now() + datetime.timedelta(days=30)
                    subscription.is_active = True
                    subscription.save()
                    return Response({"detail": "Upgraded to premium successfully."}, status=status.HTTP_200_OK)

                elif subscription.subscription_type == 'premium':
                    subscription.renew_subscription()
                    return Response({"detail": "Subscription renewed successfully."}, status=status.HTTP_200_OK)

            except Subscription.DoesNotExist:
                return Response({"detail": "No subscription found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Payment failed."}, status=status.HTTP_402_PAYMENT_REQUIRED)


class PaymentHistoryView(APIView):
    def get(self, request):
        payments = Payment.objects.filter(user=request.user)

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        comment = serializer.save()
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'comments_comments',
            {
                'type': 'comment_message',
                'message': f'New comment by {comment.user.username} on {comment.video.title}'
            }
        )


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
