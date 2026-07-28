from . import views
from django.urls import path

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register-user"),
    path("logout/", views.logout_view, name="logout"),
    path("search/", views.search_view, name="search-users"),
    path("send-invite/<int:id>", views.send_invite, name="send-invite"),
    path("chat-details/<int:id>", views.chat_details_view, name="chat-details"),
    path("send-message/<int:id>", views.send_message, name="send-message"),
    path("friend-requests/", views.friend_request_list_view, name="friend-requests"),
    path("accept-requests/<int:id>", views.accept_friend_request, name="accept-friend"),
    path("map/", views.map_view, name="map"),
    path("map/update-location/", views.update_location, name="update-location"),
    path("api/friends/", views.api_friends, name="api-friends"),
    path("notifications/", views.notifications_view, name="notifications"),
]