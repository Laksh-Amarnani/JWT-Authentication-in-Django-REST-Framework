from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        # A temporary user lets the "too similar to username" check run.
        user = User(username=self.initial_data.get('username'))
        password_validation.validate_password(value, user)
        return value

    def create(self, validated_data):
        # create_user hashes the password instead of saving it as plain text.
        return User.objects.create_user(**validated_data)
