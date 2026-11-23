"""Проверка бизнес-статуса даже для ранее выданных JWT."""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserStatus


class EmployeeJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationFailed('Вход сотрудника отключён.', code='user_inactive')
        return user


class EmployeeTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.status != UserStatus.ACTIVE:
            raise AuthenticationFailed('Вход сотрудника отключён.', code='user_inactive')
        return data
