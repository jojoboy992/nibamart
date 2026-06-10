import os
import random
import json
from email.mime.image import MIMEImage

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives

from .forms import *
from .models import EmailVerification, CustomUser, Product
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


User = get_user_model()


class CustomLoginView(LoginView):
    authentication_form = CustomLoginForm
    template_name = "login.html"


def signup_view(request):
    if request.method == "POST":
        # ✅ Add these two lines
        email = request.POST.get("email", "").strip()
        if email:
            CustomUser.objects.filter(email=email, is_active=False).delete()

        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            code = str(random.randint(100000, 999999))
            EmailVerification.objects.create(user=user, code=code)
            print(f"Generated verification code: {code} for {user.email}")

            html_content = render_to_string(
                "emails/email.html", {"user": user, "code": code}
            )
            text_content = strip_tags(html_content)

            email_msg = EmailMultiAlternatives(
                subject="Your Verification Code",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email_msg.attach_alternative(html_content, "text/html")

            try:
                logo_path = os.path.join(
                    settings.BASE_DIR, "static/img/niba_mart_picture.jpg"
                )
                with open(logo_path, "rb") as f:
                    logo = MIMEImage(f.read())
                    logo.add_header("Content-ID", "<niba_logo>")
                    email_msg.attach(logo)
                print("Logo image attached successfully.")
            except FileNotFoundError:
                print("Logo image not found at path:", logo_path)
            except Exception as e:
                print("Error attaching logo image:", e)

            try:
                email_msg.send()
                print(f"Verification email sent to {user.email}")
            except Exception as e:
                print(f"Failed to send email to {user.email}: {e}")

            request.session["pending_user"] = user.id
            return redirect("verify_email")
        else:
            print("Signup form is invalid.")
    else:
        form = CustomSignupForm()
    return render(request, "signup.html", {"form": form})


def verify_email_view(request):
    user_id = request.session.get("pending_user")
    user_email = None

    if user_id:
        try:
            user_email = CustomUser.objects.get(id=user_id).email
        except CustomUser.DoesNotExist:
            pass

    if request.method == "POST":
        code_entered = request.POST.get("code")
        if not user_id:
            return redirect("signup")

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return redirect("signup")

        verification = EmailVerification.objects.filter(
            user=user, code=code_entered
        ).last()

        if verification and verification.is_valid():
            user.is_active = True
            user.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("home")
        else:
            return render(request, "verify_email.html", {
                "error": "Invalid or expired code",
                "user_email": user_email,  # ✅
            })

    return render(request, "verify_email.html", {
        "user_email": user_email,  # ✅
    })

def resend_verification_code_view(request):
    if request.method != "POST":
        return redirect("verify_email")

    user_id = request.session.get("pending_user")
    if not user_id:
        return redirect("signup")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect("signup")

    # Rate limit: block resend if last code is less than 60s old
    last = EmailVerification.objects.filter(user=user).last()
    if last:
        elapsed = timezone.now() - last.created_at
        cooldown = timedelta(seconds=60)
        if elapsed < cooldown:
            remaining = int((cooldown - elapsed).total_seconds())
            return render(request, "verify_email.html", {
                "error": f"Please wait {remaining} second(s) before requesting a new code.",
                "user_email": user.email,
            })

    # Invalidate old codes, issue a fresh one
    EmailVerification.objects.filter(user=user).delete()
    new_code = str(random.randint(100000, 999999))
    EmailVerification.objects.create(user=user, code=new_code)

    # Build email the same way as signup_view
    html_content = render_to_string("emails/email.html", {"user": user, "code": new_code})
    text_content = strip_tags(html_content)

    email_msg = EmailMultiAlternatives(
        subject="Your new Verification Code",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email_msg.attach_alternative(html_content, "text/html")

    try:
        logo_path = os.path.join(settings.BASE_DIR, "static/img/niba_mart_picture.jpg")
        with open(logo_path, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<niba_logo>")
            email_msg.attach(logo)
    except FileNotFoundError:
        print("Logo image not found at path:", logo_path)
    except Exception as e:
        print("Error attaching logo image:", e)

    try:
        email_msg.send()
    except Exception as e:
        print(f"Failed to send resend email: {e}")
        return render(request, "verify_email.html", {
            "error": "Failed to send email. Please try again shortly.",
            "user_email": user.email,
        })

    return render(request, "verify_email.html", {
        "success": "A new code has been sent to your email.",
        "user_email": user.email,
    })


@login_required
def complete_profile_view(request):
    profile = getattr(request.user, "profile", None)

    if request.method == "POST":
        form = CompleteProfileForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            # Save username only if provided (Google users)
            username = form.cleaned_data.get("username")
            if username:
                request.user.username = username
                request.user.save()

            # Save avatar to profile
            avatar = form.cleaned_data.get("avatar")
            if avatar:
                profile.avatar = avatar
                profile.save()

            return redirect("home")

    else:
        form = CompleteProfileForm(user=request.user)

    return render(request, "complete_profile.html", {"form": form})


def logout_view(request):
    logout(request)
    request.session.flush()  # Clears all session data completely
    return redirect("home")


def get_filtered_products(request):
    query = request.GET.get("q")  # search query
    category = request.GET.get("category")  # category filter

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(seller__username__icontains=query)
        )

    if category and category != "":
        products = products.filter(category=category)

    return products.order_by("-created_at"), query, category


def home(request):
    products, _, _ = get_filtered_products(request)
    return render(
        request,
        "index.html",
        {"products": products[:3]},  # Slice to limit to 3 products
    )


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")


def user_profile(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    products = user.products.all()
    profile = getattr(user, "profile", None)
    return render(
        request,
        "profile.html",
        {
            "profile_user": user,
            "profile": profile,
            "products": products,
        },
    )


@login_required
def edit_profile(request):
    user = request.user
    profile = user.profile

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            # Save username but not email
            user_obj = user_form.save(commit=False)
            user_obj.email = user.email  # lock email
            user_obj.save()

            profile_form.save()
            return redirect("user_profile", username=user.username)

    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(
        request,
        "edit_profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


def products(request):
    products, query, category = get_filtered_products(request)

    return render(
        request,
        "products.html",
        {
            "products": products,
            "categories": dict(Product.CATEGORY_CHOICES),
            "selected_category": category,
            "search_query": query,
        },
    )


@login_required
def create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user  # attach logged-in user
            product.save()
            return redirect("products")  # after posting, go back to marketplace
    else:
        form = ProductForm()

    return render(request, "create_product.html", {"form": form})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "product_details.html", {"product": product})


@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Only seller or superuser can delete
    if request.user == product.seller or request.user.is_superuser:
        if request.method == "POST":
            product.delete()
            messages.success(request, "Product deleted successfully!")
            return redirect("products")
        return render(request, "delete_product.html", {"product": product})
    else:
        messages.error(request, "You don't have permission to delete this product.")
        return redirect("product_details", pk=product.pk)


@login_required
def get_messages(request, username):
    other_user = get_object_or_404(CustomUser, username=username)
    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        recipient__in=[request.user, other_user]
    ).order_by("timestamp")

    return JsonResponse(
        {
            "other_user": {
                "username": other_user.username,
                "email": other_user.email,
                "avatar": (
                    other_user.profile.avatar.url
                    if hasattr(other_user, "profile") and other_user.profile.avatar
                    else "/static/images/default.png"
                ),
            },
            "messages": [
                {
                    "id": msg.id,
                    "sender": msg.sender.username,
                    "recipient": msg.recipient.username,
                    "content": msg.content,
                    "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M"),
                    "unread": (msg.recipient == request.user and not msg.is_read),  # 👈 NEW
                }
                for msg in messages
            ],
        }
    )

# Update your chat_page view too
@login_required
def chat_page(request):
    # Get all users you sent messages to or received messages from
    sent_to = Message.objects.filter(sender=request.user).values_list(
        "recipient_id", flat=True
    )
    received_from = Message.objects.filter(recipient=request.user).values_list(
        "sender_id", flat=True
    )
    user_ids = set(sent_to) | set(received_from)

    users = list(CustomUser.objects.filter(id__in=user_ids))

    # Check if we need to auto-select a user
    to_username = request.GET.get("to")
    selected_user = None
    if to_username:
        selected_user = get_object_or_404(CustomUser, username=to_username)
        # Ensure selected user is in the contact list
        if selected_user not in users:
            users.insert(0, selected_user)

    # --- NEW: compute unread message counts per user ---
    counts = (
        Message.objects.filter(recipient=request.user, is_read=False)
        .values("sender__username")
        .annotate(count=Count("id"))
    )
    unread_counts = {item["sender__username"]: item["count"] for item in counts}

    return render(
        request,
        "chat.html",
        {
            "users": users,
            "selected_user": selected_user,
            "unread_counts": unread_counts,  # send to template
        },
    )

@login_required
@require_http_methods(["POST"])
def update_status(request):
    try:
        # Handle both JSON and FormData (for sendBeacon)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        status = data.get("status")

        if status not in ["online", "away", "offline"]:
            return JsonResponse({"error": "Invalid status"}, status=400)

        user_status, created = UserStatus.objects.get_or_create(user=request.user)
        user_status.status = status
        user_status.last_seen = timezone.now()
        user_status.save()

        # Broadcast status change to WebSocket consumers
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "status_updates",
                {
                    "type": "status_broadcast",
                    "username": request.user.username,
                    "status": status,
                    "timestamp": timezone.now().isoformat(),
                },
            )

        return JsonResponse({"success": True, "status": status})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def heartbeat(request):
    """Endpoint to receive heartbeat from active users"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        status = data.get("status", "online")

        user_status, created = UserStatus.objects.get_or_create(user=request.user)
        user_status.status = status
        user_status.last_seen = timezone.now()
        user_status.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def get_user_statuses(request):
    """Get status of all users with offline detection"""
    users_with_status = []

    # Time threshold for considering users offline
    offline_threshold = timezone.now() - timedelta(seconds=60)  # 60 seconds
    away_threshold = timezone.now() - timedelta(minutes=5)  # 5 minutes

    for user in CustomUser.objects.exclude(id=request.user.id):
        try:
            user_status = user.user_status
            last_seen = user_status.last_seen

            # Auto-detect offline status based on last activity
            if last_seen < offline_threshold:
                # User hasn't been active for more than 60 seconds
                if user_status.status != "offline":
                    user_status.status = "offline"
                    user_status.save()
                status = "offline"
            elif last_seen < away_threshold and user_status.status == "online":
                # User hasn't been active for more than 5 minutes but less than 60 seconds
                user_status.status = "away"
                user_status.save()
                status = "away"
            else:
                status = user_status.status

        except UserStatus.DoesNotExist:
            status = "offline"
            last_seen = None

        users_with_status.append(
            {
                "username": user.username,
                "email": user.email,
                "status": status,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "avatar": (
                    user.profile.avatar.url
                    if hasattr(user, "profile") and user.profile.avatar
                    else "/static/images/default.png"
                ),
            }
        )

    return JsonResponse({"users": users_with_status})


@login_required
@require_POST
def delete_message(request, message_id):
    try:
        msg = Message.objects.get(id=message_id, sender=request.user)
        room_name = "_".join(sorted([msg.sender.username, msg.recipient.username]))
        msg.delete()

        # 🔥 Broadcast to websocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{room_name}",
            {
                "type": "delete_message_event",
                "message_id": message_id,
            },
        )

        return JsonResponse({"success": True})
    except Message.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Message not found"}, status=404
        )


@login_required
def unread_count(request):
    """Return the unread message count for the logged-in user."""
    count = Message.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    return JsonResponse({"unread_count": count})


@login_required
def mark_read(request, username):
    if request.method == "POST":
        # Count how many messages will be marked as read
        updated_count = Message.objects.filter(
            sender__username=username,
            recipient=request.user,
            is_read=False
        ).count()
        
        # Mark messages as read
        Message.objects.filter(
            sender__username=username,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

        # Get new total unread count
        total_unread_count = Message.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()

        # ✅ Send live update to NotificationsConsumer with per-user data
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f"notifications_{request.user.username}",
            {
                "type": "new_message",
                "unread_count": total_unread_count,
                "sender": username,  # ✅ Add sender info
                "sender_unread_count": 0,  # ✅ Now 0 since we marked all as read
            }
        )

        return JsonResponse({
            "success": True, 
            "updated": updated_count,  # How many were marked as read
            "unread_count": total_unread_count
        })
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def unread_counts_per_user(request):
    from django.db.models import Count, Q
    counts = (
        Message.objects.filter(recipient=request.user, is_read=False)
        .values("sender__username")
        .annotate(count=Count("id"))
    )
    # Convert to dict: {"username": count}
    data = {item["sender__username"]: item["count"] for item in counts}
    return JsonResponse({"unread_counts": data})
