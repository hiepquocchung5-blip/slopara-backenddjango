from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user_with_stamp_validation(user_id, token_stamp):
    """Validates user and enforces single-device stamp for WebSockets."""
    try:
        user = User.objects.get(id=user_id)
        if str(user.security_stamp) == token_stamp:
            return user
    except User.DoesNotExist:
        pass
    return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom Middleware for Django Channels.
    Extracts the JWT token from the query string (?token=...) and securely 
    attaches the authenticated User instance to the WebSocket scope.
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            try:
                validated_token = UntypedToken(token)
                user_id = validated_token.payload.get('user_id')
                stamp = validated_token.payload.get('stamp')
                
                scope['user'] = await get_user_with_stamp_validation(user_id, stamp)
            except (InvalidToken, TokenError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)