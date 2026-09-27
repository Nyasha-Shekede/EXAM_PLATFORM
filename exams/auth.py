from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self,request,username=None,password=None,**kwargs):
        User=get_user_model(); identifier=username or kwargs.get(User.USERNAME_FIELD)
        if not identifier or not password: return None
        try: user=User.objects.get(username__iexact=identifier)
        except User.DoesNotExist:
            matches=User.objects.filter(email__iexact=identifier)
            if matches.count()!=1: return None
            user=matches.first()
        return user if user.check_password(password) and self.user_can_authenticate(user) else None
