"""Data access for users (Beanie queries)."""

from beanie import PydanticObjectId

from app.users.models import User


async def get_by_id(user_id: PydanticObjectId) -> User | None:
    return await User.get(user_id)


async def get_by_phone(phone: str) -> User | None:
    return await User.find_one(User.phone == phone)


async def get_by_email(email: str) -> User | None:
    return await User.find_one(User.email == email)


async def get_by_google_sub(subject: str) -> User | None:
    return await User.find_one(User.google_sub == subject)


async def get_by_apple_sub(subject: str) -> User | None:
    return await User.find_one(User.apple_sub == subject)


async def insert(user: User) -> User:
    return await user.insert()
