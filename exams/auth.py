from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = username or kwargs.get(User.USERNAME_FIELD)
        if not identifier or password is None:
            return None
        matches = User.objects.filter(username__iexact=identifier)
        if not matches.exists():
            matches = User.objects.filter(email__iexact=identifier)
        if matches.count() != 1:
            # Equalize password-hashing work and fail closed on legacy ambiguous usernames.
            User().set_password(password)
            return None
        user = matches.first()
        return user if user.check_password(password) and self.user_can_authenticate(user) else None
