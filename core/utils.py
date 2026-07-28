from django.db.models import Q

from .models import FriendRequest


def are_friends(user, other_user):
    if user == other_user:
        return True

    return FriendRequest.objects.filter(
        status=FriendRequest.StatusChoice.ACCEPTED,
    ).filter(
        (Q(from_user=user, to_user=other_user))
        | (Q(from_user=other_user, to_user=user))
    ).exists()



