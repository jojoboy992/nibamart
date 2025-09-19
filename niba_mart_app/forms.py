import re
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import *
from django.contrib.auth import get_user_model


class CustomSignupForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Username or Brandname"}
        ),
        label="Username/Brandname",
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Student Email"}
        ),
        label="Student Email",
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Phone Number"}
        )
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Password"}
        ),
        label="Password",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Confirm Password"}
        ),
        label="Confirm Password",
    )

    class Meta:
        model = CustomUser
        fields = ["username", "email", "phone_number", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        pattern = r"^\d{9}@(nileuniversity\.edu\.ng|bazeuniversity\.edu\.ng)$"
        if not re.match(pattern, email):
            raise forms.ValidationError(
                "Only valid Nile or Baze University student emails are allowed."
            )
        return email


class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Student Email"}
        ),
        label="Student Email",
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Password"}
        ),
    )


User = get_user_model()


class CompleteProfileForm(forms.ModelForm):
    username = forms.CharField(
        label="Username/Brandname",
        required=False,  # only required for Google users
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "Choose a unique username"}
        ),
    )
    avatar = forms.ImageField(
        label="Profile Picture",
        required=True,
        widget=forms.FileInput(attrs={"class": "form-input"}),
    )

    class Meta:
        model = User
        fields = ["username"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Pre-fill username for normal users
        if self.user and self.user.username:
            self.fields["username"].initial = self.user.username
            self.fields["username"].required = (
                False  # normal users don't need to edit username
            )
        else:
            # Google users need a username
            self.fields["username"].required = True

    def clean_username(self):
        username = self.cleaned_data.get("username")

        # Only validate username if required (i.e., Google users)
        if self.fields["username"].required:
            if not username:
                raise forms.ValidationError("Username is required for Google users.")
            if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
                raise forms.ValidationError("This username is already taken.")
        return username


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "avatar",
            "bio",
            "phone",
            "address",
            "facebook",
            "twitter",
            "instagram",
            "linkedin",
        ]
        labels = {
            "avatar": "Profile Picture",
            "bio": "About You / Bio",
            "phone": "Phone Number",
            "address": "Address",
            "facebook": "Facebook URL",
            "twitter": "X URL",
            "instagram": "Instagram URL",
            "linkedin": "LinkedIn URL",
        }
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "bio": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "phone": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Phone number"}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-input", "rows": 2, "placeholder": "Address"}
            ),
            "facebook": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://facebook.com/yourprofile",
                }
            ),
            "twitter": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://x.com/yourprofile",
                }
            ),
            "instagram": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://instagram.com/yourprofile",
                }
            ),
            "linkedin": forms.URLInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "https://linkedin.com/in/yourprofile",
                }
            ),
        }

    def normalize_url(self, url):
        """Ensure URL has a scheme, default to https if missing."""
        url = url.strip()
        if url and not re.match(r'^https?://', url):
            url = 'https://' + url
        return url

    def validate_domain(self, url, expected_domain, field_label):
        """Check if URL's domain ends with the expected domain."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()

        # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]

        # Match domain exactly or subdomains, e.g. 'x.com' or 'sub.x.com'
            if not domain.endswith(expected_domain):
                raise ValidationError(
                    f"The URL entered for {field_label} must be a valid {expected_domain} address."
                )
        except Exception:
            raise ValidationError(f"The URL entered for {field_label} is not a valid URL format.")


    def clean_facebook(self):
        facebook_url = self.cleaned_data.get("facebook")
        if not facebook_url:
            return facebook_url
        facebook_url = self.normalize_url(facebook_url)
        self.validate_domain(facebook_url, "facebook.com", "Facebook")
        return facebook_url

    def clean_twitter(self):
        twitter_url = self.cleaned_data.get("twitter")
        if not twitter_url:
            return twitter_url
        twitter_url = self.normalize_url(twitter_url)
        self.validate_domain(twitter_url, "x.com", "Twitter")
        return twitter_url

    def clean_instagram(self):
        instagram_url = self.cleaned_data.get("instagram")
        if not instagram_url:
            return instagram_url
        instagram_url = self.normalize_url(instagram_url)
        self.validate_domain(instagram_url, "instagram.com", "Instagram")
        return instagram_url

    def clean_linkedin(self):
        linkedin_url = self.cleaned_data.get("linkedin")
        if not linkedin_url:
            return linkedin_url
        linkedin_url = self.normalize_url(linkedin_url)
        self.validate_domain(linkedin_url, "linkedin.com", "LinkedIn")
        return linkedin_url


    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields["phone"].required = True
        if not self.instance.phone:
            self.fields["phone"].initial = "0"

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        if not phone:
            raise forms.ValidationError("Please enter your phone number.")  # Return None or empty string if it's optional

    # Now safe to call string methods
        phone = phone.strip().replace(" ", "").replace("-", "")

        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")

        if not phone.startswith("0"):
            phone = "0" + phone

        return phone




class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Username / Brand Name",
            "email": "Email Address",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(
                attrs={"class": "form-input", "readonly": "readonly"}
            ),
        }

    def clean_email(self):
        # Always return the original email, no matter what is submitted
        return self.instance.email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "quantity", "category", "condition", "image"]
        labels = {
            "name": "Product Name",
            "description": "Description",
            "price": "Price",
            "quantity": "Quantity",
            "category": "Category",
            "condition": "Condition of Product",
            "image": "Product Image",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Enter product name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter product description",
                    "rows": 4,
                }
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter price"}
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-input", "placeholder": "Enter quantity"}
            ),
            "category": forms.Select(attrs={"class": "form-input"}),
            "condition": forms.Select(attrs={"class": "form-input"}),  # <-- new dropdown
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'}),
        }