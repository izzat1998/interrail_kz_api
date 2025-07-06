from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from typing import Dict, Any, Optional

User = get_user_model()


class UserServices:
    @staticmethod
    def create_user(username: str, email: str, password: str, user_type: str = 'customer', **kwargs) -> User:
        """
        Create a new user with validation
        """
        if User.objects.filter(username=username).exists():
            raise ValueError("Username already exists")
        
        if User.objects.filter(email=email).exists():
            raise ValueError("Email already exists")
        
        if user_type not in dict(User.USER_TYPES):
            raise ValueError("Invalid user type")
        
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type,
                **kwargs
            )
            
        return user
    
    @staticmethod
    def update_user(user_id: int, **update_data) -> User:
        """
        Update user information
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User does not exist")
        
        # Check if username or email is being updated and validate uniqueness
        if 'username' in update_data:
            if User.objects.filter(username=update_data['username']).exclude(id=user_id).exists():
                raise ValueError("Username already exists")
        
        if 'email' in update_data:
            if User.objects.filter(email=update_data['email']).exclude(id=user_id).exists():
                raise ValueError("Email already exists")
        
        if 'user_type' in update_data:
            if update_data['user_type'] not in dict(User.USER_TYPES):
                raise ValueError("Invalid user type")
        
        # Update password if provided
        if 'password' in update_data:
            user.set_password(update_data.pop('password'))
        
        with transaction.atomic():
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            user.save()
        
        return user
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Soft delete user (deactivate)
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User does not exist")
        
        user.is_active = False
        user.save()
        return True
    
    @staticmethod
    def activate_user(user_id: int) -> User:
        """
        Activate a deactivated user
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User does not exist")
        
        user.is_active = True
        user.save()
        return user
    
    @staticmethod
    def change_user_type(user_id: int, new_user_type: str) -> User:
        """
        Change user type with validation
        """
        if new_user_type not in dict(User.USER_TYPES):
            raise ValueError("Invalid user type")
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User does not exist")
        
        user.user_type = new_user_type
        user.save()
        return user