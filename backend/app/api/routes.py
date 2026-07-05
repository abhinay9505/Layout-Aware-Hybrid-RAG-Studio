import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.models.schemas import ChatRequest, ChatResponse, UserRegister, UserLogin, Token
from app.services.ingestion import UploadService
from app.services.database_mgr import DocumentManager, ChatHistoryManager
from app.services.chat import ChatService
from app.core.database import users_collection
from app.core.dependencies import get_current_user, get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/v1")

upload_service = UploadService()
chat_service = ChatService()

# ── Authentication Endpoints ─────────────────────────────────

@router.post("/auth/signup", tags=["Authentication"])
async def signup(user_data: UserRegister):
    existing_user = await users_collection.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    await users_collection.insert_one({
        "user_id": user_id,
        "username": user_data.username,
        "password_hash": hashed_password
    })
    
    return {
        "success": True,
        "message": "User created successfully"
    }

@router.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: UserLogin):
    user = await users_collection.find_one({"username": credentials.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    access_token = create_access_token(data={"username": user["username"], "user_id": user["user_id"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"]
    }

@router.get("/auth/me", tags=["Authentication"])
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "user_id": current_user["user_id"]
    }

# ── RAG Endpoints ─────────────────────────────────────────────

@router.post("/documents/upload", tags=["Documents"])
async def upload_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    return await upload_service.upload(file, user_id=current_user["user_id"])

@router.get("/documents", tags=["Documents"])
async def get_documents(current_user: dict = Depends(get_current_user)):
    return await DocumentManager.get_all_documents(user_id=current_user["user_id"])

@router.delete("/documents/{document_id}", tags=["Documents"])
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    await DocumentManager.delete_document(document_id, user_id=current_user["user_id"])
    return {
        "success": True,
        "message": "Document deleted"
    }

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    return await chat_service.chat(
        request.query,
        request.session_id,
        request.top_k,
        user_id=current_user["user_id"]
    )

@router.get("/chat/history/{session_id}", tags=["Chat"])
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    history = await ChatHistoryManager.get_history(session_id, user_id=current_user["user_id"])
    return {
        "session_id": session_id,
        "messages": history
    }

@router.delete("/chat/history/{session_id}", tags=["Chat"])
async def clear_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    await ChatHistoryManager.clear_history(session_id, user_id=current_user["user_id"])
    return {
        "success": True,
        "message": "History cleared"
    }
