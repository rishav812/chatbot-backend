import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.chat_service import generate_chat_response

router = APIRouter(
    prefix="/ws",
    tags=["chat"]
)

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint for handling chat messages with the AI assistant.
    Maintains conversation history per connection.
    """
    await websocket.accept()
    
    # Store immediate conversation history for context during this WS session
    chat_history = []
    
    try:
        while True:
            # 1. Wait for message from the frontend client
            data = await websocket.receive_text()
            
            # The frontend sends: { message: "user text" }
            try:
                payload = json.loads(data)
                user_message = payload.get("message", "").strip()
            except json.JSONDecodeError:
                user_message = data.strip()
                
            if not user_message:
                continue
                
            # 2. Append user message to local history
            chat_history.append({"role": "user", "content": user_message})
            
            # 3. Generate response via OpenAI and pgvector RAG
            bot_response = await generate_chat_response(db, query=user_message, chat_history=chat_history)
            
            # 4. Append bot message to local history
            chat_history.append({"role": "assistant", "content": bot_response})
            
            # 5. Send payload back to the frontend client 
            # (Frontend expects JSON with an 'answer' or 'message' field)
            await websocket.send_json({"answer": bot_response})
            
    except WebSocketDisconnect:
        print("User disconnected from WebSocket chat.")
    except Exception as e:
        print(f"WebSocket Chat Error: {str(e)}")
        # Try to politely inform the client
        try:
            await websocket.send_json({"answer": "An internal error occurred. Let's try that again later."})
        except:
            pass
