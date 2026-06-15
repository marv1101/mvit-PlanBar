import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import verify_token, create_access_token
from app.core.exceptions import NotFoundException
from app.dependencies import get_current_user, get_db
from app.db.models.pinboard import PinboardThread, PinboardMessage, PinboardDocument
from app.db.models.user import User
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.abspath(settings.upload_dir)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "application/msword": {".doc"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "text/plain": {".txt"},
}

ALLOWED_EXTENSIONS = {}
for mime, exts in ALLOWED_MIME_TYPES.items():
    for ext in exts:
        ALLOWED_EXTENSIONS[ext] = mime

BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".vbs"}

MAX_WS_CONNECTIONS_PER_USER = 5
WS_HEARTBEAT_INTERVAL = 30
WS_HEARTBEAT_TIMEOUT = 60
WS_IDLE_TIMEOUT = 300


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


def _check_ownership(current_user: User, author_id: int):
    if current_user.id != author_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )


def _validate_magic_bytes(content: bytes, ext: str):
    MAGIC_PATTERNS = {
        ".jpg": [(b"\xff\xd8\xff", 0)],
        ".jpeg": [(b"\xff\xd8\xff", 0)],
        ".png": [(b"\x89PNG\r\n\x1a\n", 0)],
        ".gif": [(b"GIF87a", 0), (b"GIF89a", 0)],
        ".webp": [(b"RIFF", 0), (b"WEBP", 8)],
        ".pdf": [(b"%PDF", 0)],
    }
    if ext not in MAGIC_PATTERNS:
        return
    for magic, offset in MAGIC_PATTERNS[ext]:
        if len(content) < offset + len(magic) or content[offset : offset + len(magic)] != magic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content does not match expected signature.",
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
    _check_ownership(current_user, thread.author_id)
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
    _check_ownership(current_user, thread.author_id)
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
    _check_ownership(current_user, message.author_id)
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
    _check_ownership(current_user, message.author_id)
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
    _check_ownership(current_user, message.author_id)

    ext = os.path.splitext(file.filename or "file")[1].lower()

    if ext in BLOCKED_EXTENSIONS:
        logger.warning(
            f"Blocked upload attempt - user={current_user.id} file={file.filename} ext={ext}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type is not allowed.",
        )

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' is not supported.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )
    _validate_magic_bytes(content, ext)

    mime_type = ALLOWED_EXTENSIONS[ext]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(content)

    doc = PinboardDocument(
        message_id=message_id,
        file_name=file.filename or "file",
        file_path=file_path,
        file_size=len(content),
        mime_type=mime_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    doc_response = DocumentResponse.model_validate(doc)
    await _broadcast(message.thread_id, {
        "type": "document_uploaded",
        "message_id": message_id,
        "document": doc_response.model_dump(mode="json"),
    })
    return doc_response


@router.get("/documents/{document_id}")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(PinboardDocument).filter(PinboardDocument.id == document_id).first()
    if not doc:
        raise NotFoundException(detail="Document not found")
    _check_ownership(current_user, doc.message.author_id)
    if not os.path.exists(doc.file_path):
        raise NotFoundException(detail="File not found on disk")

    return FileResponse(
        doc.file_path,
        media_type=doc.mime_type,
        filename=doc.file_name,
        content_disposition_type="attachment",
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
    _check_ownership(current_user, doc.message.author_id)
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()


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
_user_connections: dict[int, int] = {}
_ws_user_map: dict[int, int] = {}
_ws_last_activity: dict[int, float] = {}


async def _connect_ws(websocket: WebSocket, thread_id: int, user_id: int):
    if _user_connections.get(user_id, 0) >= MAX_WS_CONNECTIONS_PER_USER:
        await websocket.close(code=4001, reason="Maximum connections per user reached")
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False

    await websocket.accept()
    conn_id = id(websocket)
    if thread_id not in active_connections:
        active_connections[thread_id] = []
    active_connections[thread_id].append(websocket)
    _user_connections[user_id] = _user_connections.get(user_id, 0) + 1
    _ws_user_map[conn_id] = user_id
    _ws_last_activity[conn_id] = time.time()
    return True


def _disconnect_ws(websocket: WebSocket, thread_id: int):
    conn_id = id(websocket)
    if thread_id in active_connections:
        try:
            active_connections[thread_id].remove(websocket)
        except ValueError:
            pass
        if not active_connections[thread_id]:
            del active_connections[thread_id]

    user_id = _ws_user_map.pop(conn_id, None)
    if user_id is not None:
        current_count = _user_connections.get(user_id, 0)
        if current_count > 1:
            _user_connections[user_id] = current_count - 1
        else:
            _user_connections.pop(user_id, None)

    _ws_last_activity.pop(conn_id, None)


async def _broadcast(thread_id: int, message: dict):
    if thread_id not in active_connections:
        return
    for conn in active_connections[thread_id]:
        try:
            await conn.send_json(message)
        except Exception:
            pass


def _notify_clients(thread_id: int, message: MessageResponse):
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


async def _heartbeat_loop(websocket: WebSocket, thread_id: int):
    try:
        while True:
            await asyncio.sleep(WS_HEARTBEAT_INTERVAL)
            conn_id = id(websocket)
            now = time.time()
            last_activity = _ws_last_activity.get(conn_id)

            if last_activity is not None and (now - last_activity) > WS_IDLE_TIMEOUT:
                logger.info(f"Closing idle WebSocket: user={_ws_user_map.get(conn_id)} conn={conn_id}")
                await websocket.close(code=4001, reason="Connection timeout due to inactivity")
                _disconnect_ws(websocket, thread_id)
                return

            if last_activity is not None and (now - last_activity) > WS_HEARTBEAT_TIMEOUT:
                logger.info(f"Heartbeat timeout for WebSocket: user={_ws_user_map.get(conn_id)} conn={conn_id}")
                await websocket.close(code=4001, reason="Heartbeat timeout")
                _disconnect_ws(websocket, thread_id)
                return

            await websocket.send_json({"type": "ping"})
    except Exception:
        _disconnect_ws(websocket, thread_id)


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
            logger.warning(f"WebSocket connection attempted to non-existent thread {thread_id}")
            await websocket.close(code=4004, reason="Thread not found")
            return

        token_str = token
        if not token_str:
            token_str = websocket.cookies.get("access_token", "")
        if not token_str:
            logger.warning("WebSocket auth failed: no token provided")
            await websocket.close(code=4001, reason="Missing token")
            return

        try:
            payload = verify_token(token_str)
            user_id = int(payload.get("sub", 0))
        except (ValueError, Exception) as e:
            logger.warning(f"WebSocket auth failed: invalid token - {e}")
            await websocket.close(code=4001, reason="Invalid token")
            return

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"WebSocket auth failed: user {user_id} not found in database")
            await websocket.close(code=4001, reason="User not found")
            return
    finally:
        db.close()

    logger.info(f"WebSocket authenticated: user={user_id} thread={thread_id}")

    connected = await _connect_ws(websocket, thread_id, user_id)
    if not connected:
        return

    logger.info(f"WebSocket connected: user={user_id} thread={thread_id}")

    heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket, thread_id))

    try:
        while True:
            data = await websocket.receive_text()
            conn_id = id(websocket)
            _ws_last_activity[conn_id] = time.time()

            msg_data = json.loads(data)
            msg_type = msg_data.get("type", "ping")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "pong":
                pass
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
            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id} thread={thread_id}")
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from user={user_id}")
        await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
    except Exception as e:
        logger.error(f"WebSocket error user={user_id} thread={thread_id}: {e}")
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        _disconnect_ws(websocket, thread_id)
