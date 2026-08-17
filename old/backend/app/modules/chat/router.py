"""Chat endpoints: REST (history/CRUD) + SSE streaming + WebSocket."""

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import AppContainer, Container, CurrentUser, get_current_user
from app.core.exceptions import AppError, AuthenticationError
from app.modules.chat.schemas import (
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
    SendMessageRequest,
)
from app.modules.chat.service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def _service(container: AppContainer) -> ChatService:
    return ChatService(
        container.conversations,
        container.messages,
        container.ai_router,
        container.safety,
        container.prompts,
        container.redis,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    user: CurrentUser,
    container: Container,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[ConversationResponse]:
    conversations = await _service(container).list_conversations(user, skip=skip, limit=limit)
    return [ConversationResponse(**c.model_dump()) for c in conversations]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    user: CurrentUser,
    container: Container,
    limit: int = Query(50, ge=1, le=200),
    before_id: str | None = None,
) -> list[MessageResponse]:
    messages = await _service(container).list_messages(
        user, conversation_id, limit=limit, before_id=before_id
    )
    return [MessageResponse(**m.model_dump()) for m in messages]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str, user: CurrentUser, container: Container
) -> None:
    await _service(container).delete_conversation(user, conversation_id)


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def set_feedback(
    message_id: str, req: FeedbackRequest, user: CurrentUser, container: Container
) -> None:
    await _service(container).set_feedback(user, message_id, req.feedback)


@router.post("/messages")
async def send_message_sse(
    req: SendMessageRequest, user: CurrentUser, container: Container
) -> StreamingResponse:
    """SSE stream: events `meta`, `delta`, `done`, `error`."""

    async def event_stream():
        try:
            async for event in _service(container).send_message_stream(user, req):
                payload = json.dumps(event.data, ensure_ascii=False, default=str)
                yield f"event: {event.type}\ndata: {payload}\n\n"
        except AppError as exc:
            yield f"event: error\ndata: {json.dumps(exc.to_payload(), ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    """WebSocket protocol: client sends {"token": ...} first, then
    SendMessageRequest payloads; server replies with StreamEvent frames."""
    await websocket.accept()
    container: AppContainer = websocket.app.state.container
    try:
        auth_frame = await websocket.receive_json()
        token = auth_frame.get("token", "")
        payload = container.token_service.verify_access_token(token)
        user = await container.users.get_by_id(payload["sub"])
        if user is None or not user.is_active:
            raise AuthenticationError("Foydalanuvchi topilmadi")
        await websocket.send_json({"type": "ready", "data": {}})

        service = _service(container)
        while True:
            frame = await websocket.receive_json()
            req = SendMessageRequest.model_validate(frame)
            try:
                async for event in service.send_message_stream(user, req):
                    await websocket.send_json({"type": event.type, "data": event.data})
            except AppError as exc:
                await websocket.send_json({"type": "error", "data": exc.to_payload()})
    except WebSocketDisconnect:
        return
    except AppError as exc:
        await websocket.send_json({"type": "error", "data": exc.to_payload()})
        await websocket.close(code=4401)
