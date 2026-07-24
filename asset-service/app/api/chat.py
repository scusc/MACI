import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.services.ai_delegate import run_concierge_swarm

router = APIRouter()

# In-memory connection manager for the pool chat rooms
class ConnectionManager:
    def __init__(self):
        # Maps pool_id to a list of active WebSocket connections
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, pool_id: str):
        await websocket.accept()
        if pool_id not in self.active_connections:
            self.active_connections[pool_id] = []
        self.active_connections[pool_id].append(websocket)

    def disconnect(self, websocket: WebSocket, pool_id: str):
        if pool_id in self.active_connections:
            self.active_connections[pool_id].remove(websocket)
            if not self.active_connections[pool_id]:
                del self.active_connections[pool_id]

    async def broadcast(self, message: str, pool_id: str):
        if pool_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[pool_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(dead, pool_id)

manager = ConnectionManager()

from maci_core.core.security import verify_token
from fastapi import Query

@router.websocket("/ws/chat/{pool_id}")
async def chat_endpoint(
    websocket: WebSocket, 
    pool_id: str, 
    token: str = Query(...)
):
    # Authenticate the WebSocket connection
    try:
        payload = verify_token(token, expected_type="access")
        user_id = payload.get("sub")
    except Exception as e:
        await websocket.close(code=1008) # Policy Violation (Unauthorized)
        return

    await manager.connect(websocket, pool_id)
    try:
        while True:
            # Wait for a message from a user in the group chat
            data = await websocket.receive_text()
            
            # RxJS WebSocketSubject automatically JSON.stringifies primitive strings. 
            # We must decode it if it's a valid JSON string.
            print(f"RAW WS DATA: {data}")
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, str):
                    text_content = parsed_data
                else:
                    text_content = str(parsed_data)
                print(f"PARSED DATA: {parsed_data}, TYPE: {type(parsed_data)}")
            except json.JSONDecodeError as e:
                print(f"JSON ERROR: {e}")
                text_content = data
            
            print(f"FINAL TEXT CONTENT: {text_content}")
                
            # Broadcast the user's message to everyone in the room
            await manager.broadcast(json.dumps({"sender": "User", "text": text_content}), pool_id)
            
            # Trigger the AI Concierge Swarm ONLY if explicitly called
            if text_content.strip().lower().startswith("@slice") or text_content.strip().lower().startswith("/ai"):
                # Clean the trigger from the prompt
                prompt = text_content.lower().replace("@slice", "").replace("/ai", "").strip()
                
                # TODO: Retrieve the pool's location/dates from DB using pool_id
                # destination = db.query(Pool).filter(id=pool_id).first().destination
                mock_destination = "Bali" 
                mock_date = "2026-08-01"
                
                try:
                    import asyncio
                    print("ABOUT TO CALL AI SWARM...")
                    ai_task = asyncio.create_task(run_concierge_swarm(prompt, mock_destination, mock_date))
                    
                    # Add a timeout so it doesn't hang forever and block the websocket
                    try:
                        ai_response = await asyncio.wait_for(ai_task, timeout=20.0)
                        print("AI SWARM RETURNED SUCCESSFULLY!")
                    except asyncio.TimeoutError:
                        print("AI SWARM TIMED OUT AFTER 20 SECONDS!")
                        ai_response = "The AI Concierge is taking too long to respond."
                        
                    # Broadcast the AI's response back to the room
                    await manager.broadcast(json.dumps({"sender": "Slice AI", "text": ai_response}), pool_id)
                except Exception as e:
                    print(f"AI Swarm Error: {e}")
                    import traceback
                    traceback.print_exc()
                    await manager.broadcast(json.dumps({"sender": "System", "text": f"The AI Concierge is currently unavailable. Error: {e}"}), pool_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, pool_id)
