from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str, display_name: str, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, display_name: str, **extra_fields):
        from .models import GlobalRole
        extra_fields.setdefault("global_role", GlobalRole.SA)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, display_name, **extra_fields)
