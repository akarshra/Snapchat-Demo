from django.contrib import admin
from .models import FriendRequest, Message, SnapUser

# Register your models here.
admin.site.register(FriendRequest)
admin.site.register(Message)
admin.site.register(SnapUser)