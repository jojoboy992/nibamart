from django.urls import path
from . import views
from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", signup_view, name="signup"),
    path("verify/", verify_email_view, name="verify_email"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("complete-profile/", views.complete_profile_view, name="complete_profile"),
    path("logout/", logout_view, name="logout"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    
    # Profile routes
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.user_profile, name="user_profile"),
    
    # Product routes
    path("product/new/", views.create_product, name="create_product"),
    path("products/", views.products, name="products"),
    path("product/<int:pk>/", views.product_detail, name="product_details"),
    path("product/<int:pk>/delete/", views.delete_product, name="delete_product"),

    path("chat/", views.chat_page, name="chat_page"),
    path("chat/messages/<str:username>/", views.get_messages, name="get_messages"),
    path("chat/delete/<int:message_id>/", views.delete_message, name="delete_message"),

    path('chat/update-status/', views.update_status, name='update_status'),
    path('chat/user-statuses/', views.get_user_statuses, name='get_user_statuses'),
    path('chat/heartbeat/', views.heartbeat, name='heartbeat'), 

    path("chat/unread_count/", views.unread_count, name="unread_count"),
    path("chat/mark_read/<str:username>/", views.mark_read, name="mark_read"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

