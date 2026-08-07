from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser


# Create your models here.
class SnapUser(AbstractUser):
    avatar = models.ImageField(upload_to="avatars", default="snaps/default.jpg")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    ghost_mode = models.BooleanField(default=False)


class FriendRequest(models.Model):
    class StatusChoice(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    from_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_requests",
    )
    to_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recieved_requests",
    )
    status = models.CharField(
        max_length=10, choices=StatusChoice.choices, default=StatusChoice.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"friends: {self.from_user} -> {self.to_user}: {self.status}"


class Chat(models.Model):
    class Model(models.TextChoices):
        KEEP = "keep", "Keep"
        ON_CLOSE = "on_close", "On Close"
        AFTER_24HR = "after_24hr", "After 24 Hours"

    user1 = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE, related_name="user1_chats")
    user2 = models.ForeignKey(to=get_user_model(), on_delete=models.CASCADE, related_name="user2_chats")
    model = models.CharField(max_length=16, choices=Model.choices, default=Model.ON_CLOSE)
    last_message = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    show_streak = models.BooleanField(default=True)

    def get_streak(self):
        from django.utils import timezone
        from django.utils.timezone import localdate
        from datetime import timedelta

        messages = self.messages.filter(is_system=False).exclude(image="").exclude(image__isnull=True).order_by("created_at")
        if not messages.exists():
            return 0, False

        msgs_by_date = {}
        for msg in messages:
            d = localdate(msg.created_at)
            msgs_by_date.setdefault(d, set()).add(msg.sender_id)

        today = localdate(timezone.now())
        last_msg = messages.last()
        last_msg_date = localdate(last_msg.created_at)
        if last_msg_date < today - timedelta(days=1):
            return 0, False

        streak = 0
        current_date = today

        while True:
            senders = msgs_by_date.get(current_date, set())
            if len(senders) >= 2:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                if current_date == today:
                    yesterday_senders = msgs_by_date.get(today - timedelta(days=1), set())
                    if len(yesterday_senders) >= 2:
                        current_date -= timedelta(days=1)
                        continue
                break

        return streak, (streak > 0)

    @property
    def streak_count(self):
        return self.get_streak()[0]

    @property
    def streak_active(self):
        return self.get_streak()[1]

    def __str__(self):
        return f"Chat: {self.user1} <-> {self.user2}"


class Message(models.Model):
    chat = models.ForeignKey(
        to=Chat,
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    sender = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    reciever = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recieved_messages",
    )
    is_system = models.BooleanField(default=False)
    is_viewed = models.BooleanField(default=False)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="snaps", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.sender} -> {self.reciever}"