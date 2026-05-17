from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import UserRepository, APIKeyRepository, LogRepository
from app.models.domain import User, APIKey, DetectionLog
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.rate_limit import RateLimiter
from app.core.ai_core import analyze_prompt_threat
import time
import hashlib
import uuid

class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def signup(self, email, password):
        hashed = get_password_hash(password)
        user = User(email=email, password_hash=hashed)
        return await self.repo.create(user)

    async def login(self, email, password):
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None
        return create_access_token({"sub": user.email, "user_id": user.user_id})

class AnalyzeService:
    def __init__(self, db: AsyncSession):
        self.key_repo = APIKeyRepository(db)
        self.log_repo = LogRepository(db)

    async def analyze_prompt(self, api_key_str: str, prompt: str):
        start_time = time.time()
        
        # 1. API Key Validation
        key_hash = hashlib.sha256(api_key_str.encode()).hexdigest()
        api_key = await self.key_repo.get_by_hash(key_hash)
        if not api_key:
            return {"error": "Invalid API Key", "status": 401}

        # 2. Rate Limiting
        from sqlalchemy.future import select
        from app.models.domain import User
        user_result = await self.key_repo.db.execute(select(User).where(User.user_id == api_key.user_id))
        user = user_result.scalars().first()
        
        if not await RateLimiter.check_limits(user.user_id, user.tps_limit, user.daily_quota):
            return {"error": "Rate limit exceeded", "status": 429}

        # 3. Content Analysis (Integrated with AI Developer's function)
        is_malicious, risk_score = analyze_prompt_threat(prompt)
        
        # Determine action based on boolean result from AI
        action = "blocked" if is_malicious else "allowed"
        process_time = int((time.time() - start_time) * 1000)

        # 4. Asynchronous Logging
        log = DetectionLog(
            key_id=api_key.key_id,
            raw_prompt=prompt,
            used_track="ai-model-v1",
            risk_score_pct=float(risk_score),
            action_taken=action,
            process_time_ms=process_time
        )
        
        return {
            "is_malicious": is_malicious,
            "risk_score": risk_score,
            "action": action,
            "process_time_ms": process_time,
            "log_data": log
        }

import secrets

class APIKeyManagementService:
    def __init__(self, db: AsyncSession):
        self.key_repo = APIKeyRepository(db)

    async def get_keys_for_user(self, user_id: int):
        keys = await self.key_repo.get_by_user_id(user_id)
        # We transform to frontend format. (We don't return the raw key obviously)
        # Assuming frontend expects this interface.
        return [
            {
                "id": str(k.key_id),
                "name": k.key_name,
                "key": "", # omitted for security
                "maskedKey": f"{k.key_prefix}{'•'*20}****", # We don't have the last 4 chars in DB. It's just visual.
                "createdAt": k.created_at,
                "lastUsed": None, # Should be queried from logs optimally, stub for now
                "usageCount": 0, # Should be queried from logs optimally, stub for now
                "monthlyLimit": 10000,
                "status": "active",
                "permissions": ["detect"]
            } for k in keys
        ]

    async def create_key(self, user_id: int, key_name: str):
        # Generate a real random API key
        raw_key = "pg-sk-" + secrets.token_urlsafe(36)
        key_prefix = raw_key[:10]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = APIKey(
            user_id=user_id,
            key_name=key_name,
            key_prefix=key_prefix,
            key_hash=key_hash
        )
        api_key_record = await self.key_repo.create(api_key)
        return raw_key, api_key_record

    async def delete_key(self, user_id: int, key_id: int):
        api_key = await self.key_repo.get_by_id_and_user_id(key_id, user_id)
        if api_key:
            await self.key_repo.delete(api_key)
            return True
        return False

