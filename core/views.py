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
    friend_requests = FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED
    ).filter(Q(from_user=request.user) | Q(to_user=request.user))

    friends = []
    for friend in friend_requests:
        if request.user == friend.from_user:
            friends.append(friend.to_user)
        else:
            friends.append(friend.from_user)
            
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

    messages = Message.objects.filter(
        Q(sender=request.user, reciever=friend)
        | Q(sender=friend, reciever=request.user)
    ).order_by("created_at")

    messages = list(messages)
    recieved_messages = Message.objects.filter(reciever=request.user, sender=friend)
    recieved_messages.delete()

    return render(
        request,
        "pages/chat-details.html",
        {"friend": friend, "chat_messages": messages},
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
        return redirect("home")

    message = request.POST.get("message") or ""
    snap = request.FILES.get("image")
    target = (request.POST.get("target") or "chat").strip().lower()

    if message or snap:
        recipients = get_message_recipients(request.user, friend, target)
        for recipient in recipients:
            chat = get_or_create_chat(request.user, recipient)
            Message.objects.create(
                chat=chat,
                sender=request.user,
                reciever=recipient,
                text=message,
                image=snap,
            )
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