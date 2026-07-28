from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import FriendRequest, Message
from .utils import are_friends


class AuthViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="demo",
            password="secret123",
        )

    def test_are_friends_returns_true_for_accepted_requests(self):
        friend = get_user_model().objects.create_user(
            username="friend",
            password="secret123",
        )
        FriendRequest.objects.create(
            from_user=self.user,
            to_user=friend,
            status=FriendRequest.StatusChoice.ACCEPTED,
        )

        self.assertTrue(are_friends(self.user, friend))

    def test_login_page_renders_form(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in")
        self.assertContains(response, "username")

    def test_login_with_valid_credentials_redirects_home(self):
        response = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "secret123"},
            follow=True,
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_notifications_page_renders_successfully(self):
        self.client.login(username="demo", password="secret123")
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)

    def test_send_message_to_all_friends_creates_messages_for_each_friend(self):
        self.client.login(username="demo", password="secret123")
        friend_one = get_user_model().objects.create_user(
            username="friend-one",
            password="secret123",
        )
        friend_two = get_user_model().objects.create_user(
            username="friend-two",
            password="secret123",
        )
        FriendRequest.objects.create(
            from_user=self.user,
            to_user=friend_one,
            status=FriendRequest.StatusChoice.ACCEPTED,
        )
        FriendRequest.objects.create(
            from_user=self.user,
            to_user=friend_two,
            status=FriendRequest.StatusChoice.ACCEPTED,
        )

        snap = SimpleUploadedFile("snap.jpg", b"abc123", content_type="image/jpeg")
        response = self.client.post(
            reverse("send-message", args=[friend_one.id]),
            {"target": "all_friends", "message": "hello"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Message.objects.filter(sender=self.user, reciever=friend_one).exists()
        )
        self.assertTrue(
            Message.objects.filter(sender=self.user, reciever=friend_two).exists()
        )
