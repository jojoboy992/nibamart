# niba_marts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        # Ensure Google/social accounts are always active
        if not user.is_active:
            user.is_active = True
            user.save()

        # If user doesn’t have username, flag for profile completion
        if not user.username:
            request.session["needs_username"] = True

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        if request.session.pop("needs_username", False):
            return "/complete-profile/"  # redirect to complete_profile
        return super().get_connect_redirect_url(request, socialaccount)

    def pre_social_login(self, request, sociallogin):
        """
        Automatically connect Google login to an existing account
        if the email matches.
        """
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
