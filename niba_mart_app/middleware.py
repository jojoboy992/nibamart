# niba_mart_app/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class CompleteProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile:
                # Check if the user needs to upload a profile picture
                needs_avatar = not profile.avatar or profile.avatar.name == "avatars/default.png"

                # Determine if the user is a Google user (no username yet)
                is_google_user = not request.user.username

                # Redirect rules:
                # - Google users must have username + avatar
                # - Normal users must have avatar
                if (is_google_user and (needs_avatar or not request.user.username)) or \
                   (not is_google_user and needs_avatar):

                    # Prevent redirect loop if already on complete_profile page
                    if request.path != reverse("complete_profile"):
                        return redirect("complete_profile")

        return self.get_response(request)
