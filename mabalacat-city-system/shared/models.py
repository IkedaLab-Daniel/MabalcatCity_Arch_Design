from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import identify_hasher, is_password_usable

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('hr', 'HR'),
        ('employee', 'Employee'),
        ('recruiter', 'Recruiter'),
        ('applicant', 'Applicant')
    )

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='employee')

    def save(self, *args, **kwargs):
        # Guard against accidental plaintext password saves from custom code paths.
        if self.password and is_password_usable(self.password):
            try:
                identify_hasher(self.password)
            except ValueError:
                self.set_password(self.password)

        super().save(*args, **kwargs)

    def __str__(self):
        if not self.email:
            return f"{self.username} (no email!)"
        return f"{self.username} ({self.email})"