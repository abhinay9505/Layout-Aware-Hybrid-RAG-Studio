from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse, UserRegister, UserLogin, Token
from app.services.ingestion import UploadService
from app.services.database_mgr import DocumentManager, ChatHistoryManager
from app.services.chat import ChatService
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.database import users_collection

router = APIRouter(prefix="/api/v1")

upload_service = UploadService()
chat_service = ChatService()

# ── Auth Endpoints ───────────────────────────────────────────

@router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    # Check if email already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed = hash_password(user_data.password)
    user = {
        "email": user_data.email,
        "hashed_password": hashed
    }
    await users_collection.insert_one(user)
    
    # Generate token
    token = create_access_token({"sub": user_data.email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await users_collection.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = create_access_token({"sub": user_data.email})
    return {"access_token": token, "token_type": "bearer"}

# ── Secured RAG Endpoints ─────────────────────────────────────

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    return await upload_service.upload(file, user_id=current_user["_id"])

@router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    return await DocumentManager.get_all_documents(user_id=current_user["_id"])

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, current_user: dict = Depends(get_current_user)):
    await DocumentManager.delete_document(document_id, user_id=current_user["_id"])
    return {
        "success": True,
        "message": "Document deleted"
    }

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    return await chat_service.chat(
        request.query,
        request.session_id,
        request.top_k,
        user_id=current_user["_id"]
    )

@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    history = await ChatHistoryManager.get_history(session_id, user_id=current_user["_id"])
    return {
        "session_id": session_id,
        "messages": history
    }

@router.delete("/chat/history/{session_id}")
async def clear_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    await ChatHistoryManager.clear_history(session_id, user_id=current_user["_id"])
    return {
        "success": True,
        "message": "History cleared"
    }
