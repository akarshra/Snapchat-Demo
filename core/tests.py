from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import FriendRequest, Message, Chat
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

    def test_streak_calculation(self):
        from django.utils import timezone
        from datetime import timedelta
        from core.models import Chat, Message

        friend = get_user_model().objects.create_user(
            username="friend-three",
            password="secret123",
        )
        chat = Chat.objects.create(user1=self.user, user2=friend, last_message=timezone.now())

        # No messages initially: streak is 0, not active
        streak_count, streak_active = chat.get_streak()
        self.assertEqual(streak_count, 0)
        self.assertFalse(streak_active)

        # Yesterday's messages (both users must send a message)
        yesterday = timezone.now() - timedelta(days=1)
        mock_image = SimpleUploadedFile("snap.jpg", b"abc123", content_type="image/jpeg")
        m1 = Message.objects.create(chat=chat, sender=self.user, reciever=friend, image=mock_image)
        m1.created_at = yesterday
        m1.save()

        m2 = Message.objects.create(chat=chat, sender=friend, reciever=self.user, image=mock_image)
        m2.created_at = yesterday
        m2.save()

        # Streak should be 1, active is True (since today is still open)
        streak_count, streak_active = chat.get_streak()
        self.assertEqual(streak_count, 1)
        self.assertTrue(streak_active)

        # Today's messages (both users send messages)
        m3 = Message.objects.create(chat=chat, sender=self.user, reciever=friend, image=mock_image)
        m3.created_at = timezone.now()
        m3.save()

        m4 = Message.objects.create(chat=chat, sender=friend, reciever=self.user, image=mock_image)
        m4.created_at = timezone.now()
        m4.save()

        # Streak should be 2, active is True
        streak_count, streak_active = chat.get_streak()
        self.assertEqual(streak_count, 2)
        self.assertTrue(streak_active)

    def test_toggle_streak_option_endpoint(self):
        from core.models import Chat
        from django.utils import timezone
        import json

        friend = get_user_model().objects.create_user(
            username="friend-four",
            password="secret123",
        )
        chat = Chat.objects.create(user1=self.user, user2=friend, last_message=timezone.now())

        self.assertTrue(chat.show_streak)

        self.client.login(username="demo", password="secret123")
        response = self.client.post(
            reverse("update-chat-streak-option", args=[friend.id]),
            data=json.dumps({"show_streak": False}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        chat.refresh_from_db()
        self.assertFalse(chat.show_streak)

    def test_ghost_mode_toggle_and_map_filtering(self):
        import json
        friend = get_user_model().objects.create_user(
            username="friend-ghost",
            password="secret123",
        )
        # Establish friendship
        FriendRequest.objects.create(
            from_user=self.user, to_user=friend, status=FriendRequest.StatusChoice.ACCEPTED
        )
        
        self.assertFalse(friend.ghost_mode)

        # Log in as friend and toggle ghost mode
        self.client.login(username="friend-ghost", password="secret123")
        response = self.client.post(
            reverse("toggle-ghost-mode"),
            data=json.dumps({"ghost_mode": True}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        friend.refresh_from_db()
        self.assertTrue(friend.ghost_mode)

        # Log in as self and access map view: friend should be filtered out
        self.client.login(username="demo", password="secret123")
        response = self.client.get(reverse("map"))
        self.assertEqual(response.status_code, 200)
        # Verify friend is NOT in map data JSON context
        self.assertNotIn("friend-ghost", response.content.decode())

    def test_relationship_emojis_and_message_statuses(self):
        from django.utils import timezone
        friend = get_user_model().objects.create_user(
            username="friend-emoji",
            password="secret123",
        )
        FriendRequest.objects.create(
            from_user=self.user, to_user=friend, status=FriendRequest.StatusChoice.ACCEPTED
        )

        chat = Chat.objects.create(user1=self.user, user2=friend, last_message=timezone.now())

        # No messages initially, dynamic status "Tap to chat"
        self.client.login(username="demo", password="secret123")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Tap to chat")

        # Send 1 message from self -> friend
        msg = Message.objects.create(chat=chat, sender=self.user, reciever=friend, text="test")
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Delivered") # sender = self, not viewed

        # Mark viewed and check
        msg.is_viewed = True
        msg.save()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Opened") # sender = self, viewed

    def test_screenshot_notification_endpoint(self):
        from django.utils import timezone
        friend = get_user_model().objects.create_user(
            username="friend-ss",
            password="secret123",
        )
        chat = Chat.objects.create(user1=self.user, user2=friend, last_message=timezone.now())

        self.client.login(username="demo", password="secret123")
        response = self.client.post(
            reverse("trigger-screenshot-notification", args=[friend.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)

        # Check that no system message is written to the DB
        sys_msgs = Message.objects.filter(chat=chat, is_system=True)
        self.assertFalse(sys_msgs.exists())

    def test_chat_sorting_and_last_message_updates(self):
        from django.utils import timezone
        from datetime import timedelta
        from core.models import Chat

        friend1 = get_user_model().objects.create_user(
            username="friend-sorting-1", password="secret123"
        )
        friend2 = get_user_model().objects.create_user(
            username="friend-sorting-2", password="secret123"
        )

        # Establish friendships
        FriendRequest.objects.create(
            from_user=self.user, to_user=friend1, status=FriendRequest.StatusChoice.ACCEPTED
        )
        FriendRequest.objects.create(
            from_user=self.user, to_user=friend2, status=FriendRequest.StatusChoice.ACCEPTED
        )

        chat1 = Chat.objects.create(user1=self.user, user2=friend1, last_message=timezone.now() - timedelta(hours=2))
        chat2 = Chat.objects.create(user1=self.user, user2=friend2, last_message=timezone.now() - timedelta(hours=1))

        self.client.login(username="demo", password="secret123")

        # Initial order check: friend2 is more recently active than friend1
        response = self.client.get(reverse("home"))
        friends_list = list(response.context["friends"])
        # Find position of friend-sorting-1 and friend-sorting-2
        usernames = [f.username for f in friends_list]
        idx1 = usernames.index("friend-sorting-1")
        idx2 = usernames.index("friend-sorting-2")
        self.assertTrue(idx2 < idx1) # friend2 comes before friend1

        # Send message to friend1 to make it the most recently active chat
        response = self.client.post(
            reverse("send-message", args=[friend1.id]),
            data={"message": "hello active chat"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)

        # Now chat1.last_message is updated, and friend1 should be at the top of the list!
        response = self.client.get(reverse("home"))
        friends_list = list(response.context["friends"])
        usernames = [f.username for f in friends_list]
        idx1 = usernames.index("friend-sorting-1")
        idx2 = usernames.index("friend-sorting-2")
        self.assertTrue(idx1 < idx2) # friend1 comes before friend2
