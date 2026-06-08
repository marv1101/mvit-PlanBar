import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import verify_token
from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db
from app.db.models.pinboard import PinboardThread, PinboardMessage, PinboardDocument
from app.db.models.user import User
from app.db.database import SessionLocal

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "pinboard")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ThreadUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    is_pinned: Optional[bool] = None


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)


class DocumentResponse(BaseModel):
    id: int
    message_id: int
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    thread_id: int
    author_id: int
    author_name: str = ""
    content: str
    documents: list[DocumentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ThreadResponse(BaseModel):
    id: int
    title: str
    author_id: int
    author_name: str = ""
    is_pinned: bool = False
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ThreadDetailResponse(BaseModel):
    id: int
    title: str
    author_id: int
    author_name: str = ""
    is_pinned: bool = False
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _thread_to_response(thread: PinboardThread) -> ThreadResponse:
    messages = thread.messages or []
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        author_id=thread.author_id,
        author_name=thread.author.username if thread.author else "",
        is_pinned=thread.is_pinned,
        message_count=len(messages),
        last_message_at=messages[-1].created_at if messages else None,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def _message_to_response(message: PinboardMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        author_id=message.author_id,
        author_name=message.author.username if message.author else "",
        content=message.content,
        documents=[DocumentResponse.model_validate(doc) for doc in (message.documents or [])],
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _thread_to_detail_response(thread: PinboardThread) -> ThreadDetailResponse:
    return ThreadDetailResponse(
        id=thread.id,
        title=thread.title,
        author_id=thread.author_id,
        author_name=thread.author.username if thread.author else "",
        is_pinned=thread.is_pinned,
        messages=[_message_to_response(msg) for msg in (thread.messages or [])],
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


@router.get("/threads", response_model=list[ThreadResponse])
def list_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    threads = (
        db.query(PinboardThread)
        .order_by(PinboardThread.is_pinned.desc(), PinboardThread.updated_at.desc())
        .all()
    )
    return [_thread_to_response(t) for t in threads]


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(
    data: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = PinboardThread(title=data.title, author_id=current_user.id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return _thread_to_response(thread)


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread:
        raise NotFoundException(detail="Thread not found")
    return _thread_to_detail_response(thread)


@router.put("/threads/{thread_id}", response_model=ThreadResponse)
def update_thread(
    thread_id: int,
    data: ThreadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread:
        raise NotFoundException(detail="Thread not found")
    if data.title is not None:
        thread.title = data.title
    if data.is_pinned is not None:
        thread.is_pinned = data.is_pinned
    db.commit()
    db.refresh(thread)
    return _thread_to_response(thread)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread:
        raise NotFoundException(detail="Thread not found")
    for message in thread.messages or []:
        for doc in message.documents or []:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
    db.delete(thread)
    db.commit()


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_messages(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread:
        raise NotFoundException(detail="Thread not found")
    return [_message_to_response(msg) for msg in (thread.messages or [])]


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    thread_id: int,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
    if not thread:
        raise NotFoundException(detail="Thread not found")
    message = PinboardMessage(
        thread_id=thread_id,
        author_id=current_user.id,
        content=data.content,
    )
    db.add(message)
    thread.updated_at = datetime.now()
    db.commit()
    db.refresh(message)
    _notify_clients(thread_id, _message_to_response(message))
    return _message_to_response(message)


@router.put("/messages/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: int,
    data: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.query(PinboardMessage).filter(PinboardMessage.id == message_id).first()
    if not message:
        raise NotFoundException(detail="Message not found")
    if data.content is not None:
        message.content = data.content
    db.commit()
    db.refresh(message)
    return _message_to_response(message)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.query(PinboardMessage).filter(PinboardMessage.id == message_id).first()
    if not message:
        raise NotFoundException(detail="Message not found")
    for doc in message.documents or []:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    db.delete(message)
    db.commit()


@router.post("/messages/{message_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    message_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = db.query(PinboardMessage).filter(PinboardMessage.id == message_id).first()
    if not message:
        raise NotFoundException(detail="Message not found")

    ext = os.path.splitext(file.filename or "file")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = PinboardDocument(
        message_id=message_id,
        file_name=file.filename or "file",
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.get("/documents/{document_id}")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(PinboardDocument).filter(PinboardDocument.id == document_id).first()
    if not doc:
        raise NotFoundException(detail="Document not found")
    if not os.path.exists(doc.file_path):
        raise NotFoundException(detail="File not found on disk")

    return FileResponse(
        doc.file_path,
        media_type=doc.mime_type,
        filename=doc.file_name,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(PinboardDocument).filter(PinboardDocument.id == document_id).first()
    if not doc:
        raise NotFoundException(detail="Document not found")
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()


from app.core.auth import create_access_token


class WsTokenResponse(BaseModel):
    token: str
    expires_in: int


@router.get("/ws-token", response_model=WsTokenResponse)
def get_ws_token(
    current_user: User = Depends(get_current_user),
):
    token = create_access_token(subject=str(current_user.id), expires_delta=timedelta(minutes=30))
    return WsTokenResponse(token=token, expires_in=1800)


active_connections: dict[int, list[WebSocket]] = {}


async def _connect_ws(websocket: WebSocket, thread_id: int):
    await websocket.accept()
    if thread_id not in active_connections:
        active_connections[thread_id] = []
    active_connections[thread_id].append(websocket)


def _disconnect_ws(websocket: WebSocket, thread_id: int):
    if thread_id in active_connections:
        active_connections[thread_id].remove(websocket)
        if not active_connections[thread_id]:
            del active_connections[thread_id]


async def _broadcast(thread_id: int, message: dict):
    if thread_id not in active_connections:
        return
    for conn in active_connections[thread_id]:
        try:
            await conn.send_json(message)
        except Exception:
            pass


def _notify_clients(thread_id: int, message: MessageResponse):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                _broadcast(thread_id, {
                    "type": "new_message",
                    "message": message.model_dump(mode="json"),
                })
            )
    except RuntimeError:
        pass


@router.websocket("/ws/threads/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: int,
    token: str = Query(""),
):
    db = SessionLocal()
    try:
        thread_exists = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
        if not thread_exists:
            await websocket.close(code=4004, reason="Thread not found")
            return
    finally:
        db.close()

    token_str = token
    if not token_str:
        token_str = websocket.cookies.get("access_token", "")
    if not token_str:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = verify_token(token_str)
        user_id = int(payload.get("sub", 0))
    except (ValueError, Exception):
        await websocket.close(code=4001, reason="Invalid token")
        return

    await _connect_ws(websocket, thread_id)
    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            msg_type = msg_data.get("type", "ping")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "message":
                content = msg_data.get("content", "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "detail": "Content is required"})
                    continue

                db = SessionLocal()
                try:
                    message = PinboardMessage(
                        thread_id=thread_id,
                        author_id=user_id,
                        content=content,
                    )
                    db.add(message)
                    thread = db.query(PinboardThread).filter(PinboardThread.id == thread_id).first()
                    if thread:
                        thread.updated_at = datetime.now()
                    db.commit()
                    db.refresh(message)

                    msg_response = _message_to_response(message)
                    await _broadcast(thread_id, {
                        "type": "new_message",
                        "message": msg_response.model_dump(mode="json"),
                    })
                finally:
                    db.close()
    except WebSocketDisconnect:
        _disconnect_ws(websocket, thread_id)
    except Exception:
        _disconnect_ws(websocket, thread_id)
