from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
import json
import random
from .utils import are_friends
from .models import FriendRequest, Message, Chat
from . import forms


def get_message_recipients(user, friend, target):
    if target == "all_friends":
        accepted_requests = FriendRequest.objects.filter(
            status=FriendRequest.StatusChoice.ACCEPTED
        ).filter(Q(from_user=user) | Q(to_user=user))

        recipients = []
        for req in accepted_requests:
            other_user = req.to_user if req.from_user == user else req.from_user
            if other_user != user and other_user not in recipients:
                recipients.append(other_user)

        if friend not in recipients:
            recipients.insert(0, friend)
        return recipients

    return [friend]


# Create your views here.
@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = forms.RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = forms.LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("home")
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    # Get chats involving current user ordered by last active message
    chats = Chat.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).order_by('-last_message')

    friends = []
    friends_seen = set()

    for chat in chats:
        friend = chat.user2 if chat.user1 == request.user else chat.user1
        if are_friends(request.user, friend):
            if friend.id not in friends_seen:
                friends.append(friend)
                friends_seen.add(friend.id)

    # Append any friends who do not have any chat history yet
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED
    ).filter(Q(from_user=request.user) | Q(to_user=request.user))
    for req in friend_requests:
        friend = req.to_user if req.from_user == request.user else req.from_user
        if friend.id not in friends_seen:
            friends.append(friend)
            friends_seen.add(friend.id)

    from django.db.models import Count
    sent_counts = {}
    received_counts = {}
    for friend in friends:
        sent_counts[friend.id] = Message.objects.filter(sender=request.user, reciever=friend).count()
        received_counts[friend.id] = Message.objects.filter(sender=friend, reciever=request.user).count()

    u_best_friend_id = max(sent_counts, key=sent_counts.get) if any(sent_counts.values()) else None
    sorted_sent = sorted(sent_counts.items(), key=lambda x: x[1], reverse=True)
    top_3_ids = [fid for fid, count in sorted_sent[:3] if count > 0]

    for friend in friends:
        chat = get_or_create_chat(request.user, friend)
        streak_count, streak_active = chat.get_streak()
        friend.streak_count = streak_count
        friend.streak_active = streak_active and chat.show_streak

        emoji = ""
        label = ""
        f_best = Message.objects.filter(sender=friend).values('reciever_id').annotate(count=Count('id')).order_by('-count').first()
        f_best_friend_id = f_best['reciever_id'] if f_best else None
        total_exchanged = sent_counts[friend.id] + received_counts[friend.id]

        if u_best_friend_id == friend.id and f_best_friend_id == request.user.id:
            if total_exchanged > 100:
                emoji = "💕"
                label = "Super BFFs"
            elif total_exchanged > 50:
                emoji = "❤️"
                label = "BFFs"
            else:
                emoji = "💛"
                label = "Besties"
        elif friend.id in top_3_ids:
            emoji = "😊"
            label = "Best Friends"

        friend.relationship_emoji = emoji
        friend.relationship_label = label

        last_msg = Message.objects.filter(chat=chat).order_by('-created_at').first()
        if last_msg:
            friend.last_msg = last_msg
            if last_msg.is_system:
                friend.last_msg_status = last_msg.text
                friend.last_msg_icon = "fa-solid fa-circle-info text-gray-400"
                friend.last_msg_bold = False
            elif last_msg.sender == request.user:
                if last_msg.is_viewed:
                    friend.last_msg_status = "Opened"
                    friend.last_msg_icon = "fa-regular fa-paper-plane text-gray-400"
                    friend.last_msg_bold = False
                else:
                    friend.last_msg_status = "Delivered"
                    friend.last_msg_icon = "fa-solid fa-paper-plane text-blue-500"
                    friend.last_msg_bold = False
            else:
                if last_msg.is_viewed:
                    friend.last_msg_status = "Received"
                    friend.last_msg_icon = "fa-regular fa-comment text-gray-400"
                    friend.last_msg_bold = False
                else:
                    friend.last_msg_status = "New Snap" if last_msg.image else "New Message"
                    friend.last_msg_icon = "fa-solid fa-comment text-red-500"
                    friend.last_msg_bold = True
        else:
            friend.last_msg = None
            friend.last_msg_status = "Tap to chat"
            friend.last_msg_icon = "fa-regular fa-message text-gray-300"
            friend.last_msg_bold = False
            
    pending_reqs = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.PENDING, to_user=request.user
    )
   
    unread_messages = Message.objects.filter(reciever=request.user).order_by("-created_at")
    
    notifications = []
    
    for req in pending_reqs:
        notifications.append({
            "type": "friend_request",
            "title": "Friend Request",
            "text": f"{req.from_user.username} sent you a friend request.",
            "avatar_url": req.from_user.avatar.url if req.from_user.avatar else "/static/snaps/default.jpg",
            "action_url": f"/accept-requests/{req.id}",
            "req_id": req.id
        })
        
    seen_senders = set()
    for msg in unread_messages:
        if msg.sender.id not in seen_senders:
            seen_senders.add(msg.sender.id)
            notifications.append({
                "type": "message",
                "title": "New Message",
                "text": f"{msg.sender.username} sent you a snap.",
                "avatar_url": msg.sender.avatar.url if msg.sender.avatar else "/static/snaps/default.jpg",
                "action_url": f"/chat-details/{msg.sender.id}"
            })
            
    notifications_count = len(notifications)
    
    return render(
        request, 
        "pages/chat.html", 
        {
            "friends": friends, 
            "notifications": notifications, 
            "notifications_count": notifications_count
        }
    )


@login_required
def chat_details_view(request, id):
    friend = get_object_or_404(get_user_model(), pk=id)
    if not are_friends(request.user, friend):
        return redirect("home")

    chat = get_or_create_chat(request.user, friend)

    if chat.model == Chat.Model.AFTER_24HR:
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)
        Message.objects.filter(chat=chat, created_at__lt=cutoff).delete()

    # Mark incoming messages as viewed
    Message.objects.filter(chat=chat, reciever=request.user, is_viewed=False).update(is_viewed=True)

    messages = Message.objects.filter(
        Q(sender=request.user, reciever=friend)
        | Q(sender=friend, reciever=request.user)
    ).order_by("created_at")

    messages = list(messages)

    if chat.model == Chat.Model.ON_CLOSE:
        recieved_messages = Message.objects.filter(reciever=request.user, sender=friend)
        recieved_messages.delete()

    return render(
        request,
        "pages/chat-details.html",
        {"friend": friend, "chat_messages": messages, "chat": chat},
    )


@login_required
def search_view(request):
    users = []
    friends = []
    unique_friends = []
    pending = []

    search_username = request.GET.get("username")
    if search_username:
        users = (
            get_user_model()
            .objects.filter(username__icontains=search_username)
            .exclude(id=request.user.id)
        )

        queryset = FriendRequest.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user)
        )

        friends = queryset.filter(status=FriendRequest.StatusChoice.ACCEPTED)
        pending_requests = queryset.filter(status=FriendRequest.StatusChoice.PENDING)

        for friend in friends:
            if request.user == friend.from_user:
                unique_friends.append(friend.to_user.id)
            else:
                unique_friends.append(friend.from_user.id)

        for req in pending_requests:
            if request.user == req.from_user:
                pending.append(req.to_user.id)
            else:
                pending.append(req.from_user.id)

    suggested_users = []
    if not search_username:
        existing_ids = set(unique_friends) | set(pending)
        suggested_users = (
            get_user_model()
            .objects.exclude(id=request.user.id)
            .exclude(id__in=existing_ids)
            .order_by("?")[:4]
        )

    return render(
        request,
        "pages/search.html",
        {
            "users": users,
            "friends": unique_friends,
            "pending": pending,
            "search": search_username,
            "suggested_users": suggested_users,
        },
    )


def get_or_create_chat(user1, user2):
    chat = Chat.objects.filter(
        (Q(user1=user1, user2=user2) | Q(user1=user2, user2=user1))
    ).first()
    if chat:
        return chat
    return Chat.objects.create(user1=user1, user2=user2, last_message=timezone.now())


@require_http_methods(["POST"])
@login_required
def send_invite(request, id):
    if id == request.user.id:
        return redirect("search-users")
    to_user = get_object_or_404(get_user_model(), id=id)

    try:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    except IntegrityError:
        return redirect("search-users")

    return redirect("search-users")


@login_required
@require_http_methods(["POST"])
def send_message(request, id):
    friend = get_object_or_404(get_user_model(), pk=id)

    if not are_friends(request.user, friend):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": "Not friends"}, status=403)
        return redirect("home")

    message = request.POST.get("message") or ""
    snap = request.FILES.get("image")
    target = (request.POST.get("target") or "chat").strip().lower()

    if message or snap:
        recipients = get_message_recipients(request.user, friend, target)
        
        # Get channel layer for real-time WebSocket broadcast
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        for recipient in recipients:
            chat = get_or_create_chat(request.user, recipient)
            msg = Message.objects.create(
                chat=chat,
                sender=request.user,
                reciever=recipient,
                text=message,
                image=snap,
            )
            
            # Update last message time
            from django.utils import timezone
            chat.last_message = timezone.now()
            chat.save()
            
            if channel_layer:
                room_name = f"chat_{min(request.user.id, recipient.id)}_{max(request.user.id, recipient.id)}"
                room_group_name = f"chat_{room_name}"
                async_to_sync(channel_layer.group_send)(
                    room_group_name,
                    {
                        "type": "chat_message",
                        "message": {
                            "id": msg.id,
                            "sender_id": request.user.id,
                            "sender_username": request.user.username,
                            "recipient_id": recipient.id,
                            "text": msg.text,
                            "image_url": msg.image.url if msg.image else None,
                            "created_at": "Just now",
                        }
                    }
                )

                # Send real-time notification to the recipient on the home list page
                recipient_notification_group = f"user_{recipient.id}_notifications"
                async_to_sync(channel_layer.group_send)(
                    recipient_notification_group,
                    {
                        "type": "send_notification",
                        "notification": {
                            "sender_id": request.user.id,
                            "sender_username": request.user.username,
                            "type": "image" if msg.image else "text",
                            "text": "New Snap" if msg.image else "New Message",
                            "created_at": "Just now",
                        }
                    }
                )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    return redirect("chat-details", id=id)


@login_required
@require_http_methods(["GET"])
def friend_request_list_view(request):
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.PENDING, to_user=request.user
    )
    return render(
        request, "pages/friend-request.html", {"friend_requests": friend_requests}
    )


@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, id):
    req = get_object_or_404(FriendRequest, pk=id)
    if req.to_user == request.user and req.status == FriendRequest.StatusChoice.PENDING:
        req.status = FriendRequest.StatusChoice.ACCEPTED
        req.save()
    return redirect("friend-requests")


@login_required
def map_view(request):
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED
    ).filter(Q(from_user=request.user) | Q(to_user=request.user))

    friends = []
    for friend_req in friend_requests:
        if request.user == friend_req.from_user:
            friends.append(friend_req.to_user)
        else:
            friends.append(friend_req.from_user)

    user_lat = request.user.latitude
    user_lng = request.user.longitude
    base_lat = user_lat if user_lat is not None else 28.8387
    base_lng = user_lng if user_lng is not None else 78.7768

    friends_data = []
    friends_data.append({
        "id": request.user.id,
        "username": "Me",
        "avatar_url": request.user.avatar.url if request.user.avatar else "/static/snaps/default.jpg",
        "lat": user_lat,
        "lng": user_lng,
        "is_self": True,
    })

    for friend in friends:
        if friend.ghost_mode:
            continue
        lat = friend.latitude
        lng = friend.longitude
        
        if lat is None or lng is None:
            rng = random.Random(friend.id)
            lat_offset = rng.uniform(-0.015, 0.015)
            lng_offset = rng.uniform(-0.015, 0.015)
            lat = base_lat + lat_offset
            lng = base_lng + lng_offset

        friends_data.append({
            "id": friend.id,
            "username": friend.username,
            "avatar_url": friend.avatar.url if friend.avatar else "/static/snaps/default.jpg",
            "lat": lat,
            "lng": lng,
            "is_self": False,
        })

    context = {
        "friends_data": friends_data,
        "friends_json": json.dumps(friends_data),
        "base_lat": base_lat,
        "base_lng": base_lng,
        "has_location": user_lat is not None,
    }
    return render(request, "pages/map.html", context)


@login_required
@require_http_methods(["POST"])
def update_location(request):
    try:
        data = json.loads(request.body)
        lat = float(data.get("latitude"))
        lng = float(data.get("longitude"))
        
        user = request.user
        user.latitude = lat
        user.longitude = lng
        user.save()
        
        return JsonResponse({"status": "success", "message": "Location updated."})
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "message": "Invalid coordinates or request body."}, status=400)


@login_required
@require_http_methods(["POST"])
def update_chat_delete_option(request, id):
    try:
        data = json.loads(request.body)
        delete_option = data.get("delete_option")
        if delete_option not in [Chat.Model.KEEP, Chat.Model.ON_CLOSE, Chat.Model.AFTER_24HR]:
            return JsonResponse({"status": "error", "message": "Invalid option"}, status=400)
        
        friend = get_object_or_404(get_user_model(), pk=id)
        chat = get_or_create_chat(request.user, friend)
        chat.model = delete_option
        chat.save()
        
        return JsonResponse({"status": "success", "message": "Delete option updated."})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@login_required
@require_http_methods(["POST"])
def update_chat_streak_option(request, id):
    try:
        data = json.loads(request.body)
        show_streak = data.get("show_streak", True)
        friend = get_object_or_404(get_user_model(), pk=id)
        chat = get_or_create_chat(request.user, friend)
        chat.show_streak = bool(show_streak)
        chat.save()
        
        return JsonResponse({"status": "success", "message": "Streak option updated."})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_ghost_mode(request):
    try:
        data = json.loads(request.body)
        ghost_mode = data.get("ghost_mode", False)
        user = request.user
        user.ghost_mode = bool(ghost_mode)
        user.save()
        return JsonResponse({"status": "success", "ghost_mode": user.ghost_mode})
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@login_required
@require_http_methods(["POST"])
def trigger_screenshot_notification(request, id):
    friend = get_object_or_404(get_user_model(), pk=id)
    
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    if channel_layer:
        room_name = f"chat_{min(request.user.id, friend.id)}_{max(request.user.id, friend.id)}"
        room_group_name = f"chat_{room_name}"
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "is_screenshot_alert": True,
                    "sender_username": request.user.username,
                    "text": f"{request.user.username} took a screenshot!",
                }
            }
        )
        
    return JsonResponse({"status": "success"})


@login_required
@require_http_methods(["GET"])
def api_friends(request):
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED
    ).filter(Q(from_user=request.user) | Q(to_user=request.user))

    friends = []
    for friend in friend_requests:
        other = friend.to_user if friend.from_user == request.user else friend.from_user
        friends.append({
            "id": other.id,
            "username": other.username,
            "avatar_url": other.avatar.url if other.avatar else "/static/snaps/default.jpg"
        })
    return JsonResponse({"friends": friends})


@login_required
def notifications_view(request):
    pending_reqs = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.PENDING, to_user=request.user
    )
    
    unread_messages = Message.objects.filter(reciever=request.user).order_by("-created_at")
    
    notifications = []
    
    for req in pending_reqs:
        notifications.append({
            "type": "friend_request",
            "title": "Friend Request",
            "text": f"{req.from_user.username} sent you a friend request.",
            "avatar_url": req.from_user.avatar.url if req.from_user.avatar else "/static/snaps/default.jpg",
            "action_url": f"/accept-requests/{req.id}",
            "req_id": req.id
        })
        
    seen_senders = set()
    for msg in unread_messages:
        if msg.sender.id not in seen_senders:
            seen_senders.add(msg.sender.id)
            notifications.append({
                "type": "message",
                "title": "New Message",
                "text": f"{msg.sender.username} sent you a snap.",
                "avatar_url": msg.sender.avatar.url if msg.sender.avatar else "/static/snaps/default.jpg",
                "action_url": f"/chat-details/{msg.sender.id}"
            })
            
    return render(request, "pages/notifications.html", {"notifications": notifications})