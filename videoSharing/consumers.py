import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Avg
from django.db import models
from django.utils import timezone

from .models import Video, User, Rating, Subscription, WatchHistory


class VideoViewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs']['video_id']
        self.room_group_name = f'video_{self.video_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', '')
        user_id = data.get('user_id')

        if not user_id or not str(user_id).isdigit():
            await self.send(text_data=json.dumps({"error": "Invalid user_id"}))
            return

        user_id = int(user_id)
        check_allowance = await self.check_allowance(self.video_id, user_id)
        if action == 'view':
            if check_allowance:
                video = await self.increment_view_count(self.video_id)
                await self.record_watch_history(video.id, user_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'video_view_update',
                        'view_count': video.view_count
                    }
                )

    async def video_view_update(self, event):
        view_count = event['view_count']
        await self.send(text_data=json.dumps({
            'view_count': view_count
        }))

    @database_sync_to_async
    def record_watch_history(self, video_id, user_id):
        user = User.objects.get(pk=user_id)
        video = Video.objects.get(id=video_id)
        watch_history = WatchHistory(video=video, user=user, watch_date=timezone.now())
        watch_history.save()

    @database_sync_to_async
    def increment_view_count(self, video_id):
        video = Video.objects.get(id=video_id)
        video.view_count += 1
        video.save()
        return video

    @database_sync_to_async
    def check_allowance(self, video_id, user_id):
        try:
            video = Video.objects.get(id=video_id)
            user = User.objects.get(pk=user_id)
            return video.allowed_to_watch(user)
        except Video.DoesNotExist:
            print(f"Video with id {video_id} does not exist")
            return False
        except User.DoesNotExist:
            print(f"User with id {user_id} does not exist")
            return False


class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "comments"
        self.room_group_name = f'comments_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'comment_message',
                'message': message
            }
        )

    async def comment_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))


class RatingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.video_id = self.scope['url_route']['kwargs']['video_id']
        self.room_group_name = f'ratings_{self.video_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        score = data['score']
        user_id = data['user_id']

        if await self.is_premium_user(user_id):
            await self.save_rating(self.video_id, user_id, score)

            video = await self.get_video(self.video_id)

            average_rating = await self.update_average_rating(video)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'rating_update',
                    'average_rating': float(average_rating)
                }
            )
        else:
            await self.send(text_data=json.dumps({
                'error': 'You must have a premium subscription to rate this video.'
            }))

    async def rating_update(self, event):
        average_rating = event['average_rating']
        await self.send(text_data=json.dumps({
            'average_rating': average_rating
        }))

    @database_sync_to_async
    def save_rating(self, video_id, user_id, score):
        video = Video.objects.get(id=video_id)
        user = User.objects.get(id=user_id)
        rating, created = Rating.objects.update_or_create(
            user=user, video=video,
            defaults={'score': score}
        )

    @database_sync_to_async
    def update_average_rating(self, video):
        ratings = Rating.objects.filter(video=video)
        average_rating = ratings.aggregate(models.Avg('score'))['score__avg'] or 0.0
        video.average_rating = average_rating
        video.save()
        print(f'New average rating calculated: {average_rating}')
        return average_rating

    @database_sync_to_async
    def get_video(self, video_id):
        return Video.objects.get(id=video_id)

    @database_sync_to_async
    def is_premium_user(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            subscription = Subscription.objects.get(user=user)
            return subscription.subscription_type == 'premium'
        except User.DoesNotExist:
            return False
        except Subscription.DoesNotExist:
            return False
