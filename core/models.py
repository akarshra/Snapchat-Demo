from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser


# Create your models here.
class SnapUser(AbstractUser):
    avatar = models.ImageField(upload_to="avatars", default="snaps/default.jpg")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)


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
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="snaps", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.sender} -> {self.reciever}"