from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
import asyncio
from backend.dhan.dhan_client import DhanClient
from backend.angelone.angelone_client import AngeloneClient

app = FastAPI()

# Mount the frontend directory to serve static files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

templates = Jinja2Templates(directory="../frontend")

dhan_client = None
angelone_client = None

import threading

@app.on_event("startup")
async def startup_event():
    global dhan_client, angelone_client
    dhan_client = DhanClient(config_path='../config/config.json')
    angelone_client = AngeloneClient(config_path='../config/config.json')

    # Start the WebSocket connections in separate threads
    dhan_thread = threading.Thread(target=dhan_client.connect_order_update, args=(on_dhan_order_update,))
    dhan_thread.daemon = True
    dhan_thread.start()

    token_list = [
        {
            "exchangeType": 1,
            "tokens": ["26009"]
        }
    ]
    angelone_thread = threading.Thread(target=angelone_client.connect_to_websocket, args=("your_correlation_id", 1, token_list, on_angelone_order_update))
    angelone_thread.daemon = True
    angelone_thread.start()

@app.post("/api/credentials")
async def save_credentials(request: Request):
    credentials = await request.json()

    if not os.path.exists('../config'):
        os.makedirs('../config')

    with open('../config/config.json', 'w') as f:
        json.dump(credentials, f, indent=4)

    return {"message": "Credentials saved successfully"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

loop = None

@app.on_event("startup")
async def startup_event():
    global dhan_client, angelone_client, loop
    loop = asyncio.get_event_loop()
    dhan_client = DhanClient(config_path='../config/config.json')
    angelone_client = AngeloneClient(config_path='../config/config.json')

    # Start the WebSocket connections in separate threads
    dhan_thread = threading.Thread(target=dhan_client.connect_order_update, args=(on_dhan_order_update,))
    dhan_thread.daemon = True
    dhan_thread.start()

    token_list = [
        {
            "exchangeType": 1,
            "tokens": ["26009"]
        }
    ]
    angelone_thread = threading.Thread(target=angelone_client.connect_to_websocket, args=("your_correlation_id", 1, token_list, on_angelone_order_update))
    angelone_thread.daemon = True
    angelone_thread.start()

def on_dhan_order_update(order_data):
    # This function will be called when there is an order update from Dhan
    # We will broadcast the update to all connected clients
    asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(order_data)), loop)

def on_angelone_order_update(order_data):
    # This function will be called when there is an order update from Angel One
    # We will broadcast the update to all connected clients
    asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(order_data)), loop)

@app.websocket("/ws/trades")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We can receive messages from the client here if needed
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# In a real application, you would start these in the background
# For example, using asyncio.create_task in the startup_event
# dhan_client.connect_order_update(on_dhan_order_update)
# angelone_client.connect_to_websocket(..., on_angelone_order_update)
