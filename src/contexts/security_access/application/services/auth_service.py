from src.contexts.security_access.application.polices.auth_policies import DomainRestrictionPolicy
from src.contexts.security_access.domain.entities.user import User
from src.contexts.security_access.domain.ports.auth_provider import AuthProvider
from src.contexts.security_access.domain.repositories.user_repository import UserRepository
from src.contexts.security_access.infrastructure.mapper.token_mapper import TokenMapper

class AuthService:
    def __init__(self, auth_provider: AuthProvider , user_repository: UserRepository , token_mapper: TokenMapper, validation_policy: DomainRestrictionPolicy = None):        
        self.auth_provider = auth_provider
        self.user_repository = user_repository
        self.token_mapper = token_mapper
        self.validation_policy = validation_policy

    async def login(self, token: str) -> tuple[User, str]:
        auth_data = self.auth_provider.verify_token(token)

        if self.validation_policy:
            self.validation_policy(auth_data.email)

        user = await self.user_repository.get_by_email(str(auth_data.email))

        if not user:
            user = User.create_new_user(auth_data)
            await self.user_repository.save(user)
        else:
            await self._sync_user(user, auth_data)

        access_token = self.token_mapper.create_token_from_user(user)

        return user, access_token

    async def _sync_user(self, user: User, auth_data):
        user.update_profile(auth_data)
        await self.user_repository.save(user)