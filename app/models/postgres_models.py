from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.UUIDField(pk=True)
    is_admin = fields.BooleanField(default=False)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    password_hash = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)


class Session(Model):
    token = fields.CharField(max_length=512, pk=True)
    user = fields.ForeignKeyField("models.User", related_name="sessions")
    status = fields.BooleanField()
    expires_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)


class SessionHistory(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="history")
    message = fields.TextField()
    response = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
