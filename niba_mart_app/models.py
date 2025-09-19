from django.contrib.auth.models import AbstractUser, User
from django.db import models
import random
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver



class CustomUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    
class UserStatus(models.Model):
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('away', 'Away'), 
        ('offline', 'Offline'),
    ]
    
    # IMPORTANT: Use settings.AUTH_USER_MODEL, NOT User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # This must be settings.AUTH_USER_MODEL
        on_delete=models.CASCADE, 
        related_name='user_status'  # Changed from 'status' to 'user_status'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    
    @classmethod
    def get_or_create_status(cls, user):
        status, created = cls.objects.get_or_create(user=user)
        return status
    
    class Meta:
        verbose_name = "User Status"
        verbose_name_plural = "User Statuses"

class EmailVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created_at < timedelta(minutes=10) # 10min expiry


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')
    phone = models.CharField(max_length=15, blank=False, null=False)
    address = models.TextField(blank=True, null=True)

    # Social media links
    facebook = models.URLField(max_length=200, blank=True, null=True)
    twitter = models.URLField(max_length=200, blank=True, null=True)
    instagram = models.URLField(max_length=200, blank=True, null=True)
    linkedin = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
 
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('books', 'Books'),
        ('food', 'Food'),
        ('accessories', 'Accessories'),
        ('drinks', 'Drinks'),
    ]

    CONDITION_CHOICES = [
        ('brand_new', 'Brand New'),
        ('fairly_used', 'Fairly Used'),
        ('used', 'Used'),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )
    name = models.CharField(max_length=200)  # Product name/title
    description = models.TextField()  # Short description of the product
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)  # number of products available
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='brand_new')
    image = models.ImageField(upload_to="products/")  # required
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.seller.username}"


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"From {self.sender} to {self.recipient}: {self.content[:30]}"
    
