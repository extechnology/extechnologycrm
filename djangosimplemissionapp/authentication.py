from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions

class VersionedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        
        # Get the token version from the JWT payload
        token_version = validated_token.get('token_version')
        
        if token_version is None:
            raise exceptions.AuthenticationFailed('Token version missing', code='token_version_missing')
            
        # Compare with the version stored in the database
        if user.token_version != token_version:
            raise exceptions.AuthenticationFailed('Token version mismatch. Role has changed. Please log in again.', code='token_version_mismatch')
            
        return user
