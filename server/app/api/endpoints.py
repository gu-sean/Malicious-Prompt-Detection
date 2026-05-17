from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import SECRET_KEY, ALGORITHM
from app.services.logic import AuthService, AnalyzeService, APIKeyManagementService
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class PromptAnalysisRequest(BaseModel):
    prompt: str

class APIKeyCreateRequest(BaseModel):
    name: str

@router.post("/users/signup")
async def signup(user_data: UserAuth, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.signup(user_data.email, user_data.password)
    return {"message": "User created", "user_id": user.user_id}

@router.post("/users/login")
async def login(user_data: UserAuth, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    token = await service.login(user_data.email, user_data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

@router.get("/users/stats")
async def get_user_stats(user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = APIKeyManagementService(db)
    stats = await service.get_user_stats(user_id)
    return stats

@router.get("/users/keys")
async def get_api_keys(user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = APIKeyManagementService(db)
    keys = await service.get_keys_for_user(user_id)
    return keys

@router.post("/users/keys")
async def create_api_key(request: APIKeyCreateRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = APIKeyManagementService(db)
    new_key, api_key_record = await service.create_key(user_id, request.name)
    return {
        "id": str(api_key_record.key_id),
        "name": api_key_record.key_name,
        "key": new_key, # the raw key (only returned once)
        "maskedKey": f"{api_key_record.key_prefix}{'•'*20}{new_key[-4:]}",
        "createdAt": api_key_record.created_at,
        "lastUsed": None,
        "usageCount": 0,
        "monthlyLimit": 10000,
        "status": "active",
        "permissions": ["detect"]
    }

@router.delete("/users/keys/{key_id}")
async def delete_api_key(key_id: int, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = APIKeyManagementService(db)
    success = await service.delete_key(user_id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")
    return {"message": "API Key deleted"}

@router.post("/v1/analyze")
async def analyze(
    request: PromptAnalysisRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    service = AnalyzeService(db)
    result = await service.analyze_prompt(x_api_key, request.prompt)
    
    if "error" in result:
        raise HTTPException(status_code=result["status"], detail=result["error"])
    
    # Background log save
    log_data = result.pop("log_data")
    background_tasks.add_task(service.log_repo.create, log_data)
    
    return result
