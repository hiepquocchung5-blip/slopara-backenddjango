from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

class SingleDeviceJWTAuthentication(JWTAuthentication):
    """
    Validates that the JWT token matches the user's current database security stamp.
    If it doesn't, it means the user logged in elsewhere, and the token is rejected.
    """
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        
        token_stamp = validated_token.get('stamp')
        if not token_stamp or str(user.security_stamp) != token_stamp:
            raise AuthenticationFailed(
                "SESSION_TERMINATED: Account accessed from another device.", 
                code="session_terminated"
            )
            
        return user