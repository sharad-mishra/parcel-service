from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class MicroserviceJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user = type("User", (), {})()  # dummy user
            user.id = validated_token.get("user_id")
            user.role = validated_token.get("role", "customer")
            user.is_authenticated = True  # ✅ Add this line
            return user
        except Exception:
            raise AuthenticationFailed("User not found", code="user_not_found")
