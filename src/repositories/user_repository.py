from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.schemas.user_schema import UserRequest, UserUpdateRequest

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_user(self) -> list[User]:
        result = await self.db.execute(select(User))

        return list(result.scalars().all())
    
    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.get(User, user_id)

        return result
    
    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))

        return result.scalar_one_or_none()

    async def create_user(self, request: UserRequest) -> User:
        new_user = User(
            email=request.email,
            password=request.password,
            role_id=request.role_id,
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return new_user
    
    async def update_user(self, user_id: str, request: UserUpdateRequest) -> User | None:
        data = request.model_dump(exclude_none=True)
        stmt = update(User).where(User.id == user_id).values(**data)
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return await self.db.get(User, user_id)

    async def delete_user(self, user_id: str) -> bool:
        user = await self.db.get(User, user_id)
        
        if not user:
            return False
        
        await self.db.delete(user)
        await self.db.commit()

        return True

        

