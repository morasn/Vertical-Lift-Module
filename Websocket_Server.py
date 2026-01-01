import asyncio
import websockets
import threading
import json
from queue import Queue

import DB.DB_Back as db
import VLM_Control as VLM
import Backend

# Global to store connected ESP32 WebSocket
ws = None
message_queue = Queue()  # Thread-safe queue
websocket_started = False  # Add this flag

async def websocket_handler(websocket):
    global ws
    ws = websocket  
    print("ESP32 connected")
    db.log_event(
        "INFO",
        "ESP32 WebSocket Connected",
        "ESP32",
        transaction_type="WEBSOCKET_CONNECTION",
    )
    
    try:
        async for message in websocket:
            print(f"Received from ESP32: {message}")
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                print("Invalid JSON received")
                continue
            transaction_id = db.Transaction_ID_Generator()
            db.log_event(
                "INFO",
                f"Received message with code {message['code']} and content {message}",
                "ESP32",
                transaction_type="WEBSOCKET_MESSAGE",
                transaction_id=transaction_id,
            )
            match int(message["code"]):
                case 120:  # Handle authentication request from ESP32 and provide transaction ID

                    transaction_id = db.Transaction_ID_Generator()
                    operator_info = db.Operator_ID_Query(message["operator"])
                    print(f"Operator Info: {operator_info}")
                    if operator_info is not None:
                        # Send the transaction ID and operator info back to the ESP32
                        response = {
                            "code": 110,
                            "transaction_id": transaction_id,
                            "Authenticated": True,
                        }
                        print(f"Sending to ESP32: {response}, out from Function")
                        db.log_event(
                            "INFO",
                            "Operator Authenticated & Transaction Created",
                            "ESP32",
                            transaction_type="AUTHENTICATION",
                            transaction_id=transaction_id,
                        )
                        await websocket.send(json.dumps(response))
                    else:
                        response = {"code": 110, "transaction_id": transaction_id, "Authenticated": False}
                        print(f"Sending to ESP32: {response}, out from Function, Invalid Operator ID")
                        db.log_event(
                            "ERROR",
                            "Authentication Failed: Invalid Operator ID",
                            "ESP32",
                            transaction_type="AUTHENTICATION",
                            transaction_id=transaction_id,
                        )
                        await websocket.send(
                            json.dumps(response)
                        )
                case 121:  # Handle floor selection and operator info
                    transaction_id = message["transaction_id"]
                    floor_selected = message["Floors"]
                    operator_id = message["operator"]

                    db.log_event(
                        "INFO",
                        f"Floor {floor_selected} selected by Operator {operator_id}",
                        "ESP32",
                        transaction_type="FLOOR_SELECTION",
                        transaction_id=transaction_id,
                    )
                case 122: # handle UIDs sent from ESP32
                    transaction_id = message["transaction_id"]
                    uid_list = message["UIDs"][0]
                    operation = message["operation"]  
                    shelf_pos = message["Floors"][0]
                    
                    if operation == "R":
                        operation = "restock"
                        QTY = 1
                    elif operation == "D":
                        operation = "dispense"
                        QTY = -1

                    db.log_event(
                        "INFO",
                        f"UIDs {uid_list} processed for {operation} by Transaction {transaction_id}",
                        "ESP32",
                        transaction_type="UID_PROCESSING",
                        transaction_id=transaction_id,
                    )
                    Backend.Norm_Product_Operation(transaction_id, shelf_pos, uid_list, QTY, message["operator_id"], Source="ESP32", project=None)

                case 123: # Handle Auto Restock shelf get
                    transaction_id = message["transaction_id"]
                    uid = message["uid"]
                    operator_id = message["operator_id"]
                    VLM.Auto_Restock_Shelf_Get(uid, operator_id, transaction_id)

                case 130: #Handle RFID scan results without any function
                    uid = message["uid"]
                    print(f"RFID Scan Results: {uid}")
                
                case 200: # Handle VLM success update
                    try:
                        transaction_id = message["transaction_id"]
                    except KeyError:
                        transaction_id = None
                    
                    msg = message["msg"]

                    db.log_event(
                        "INFO",
                        msg,
                        "ESP32",
                        transaction_type="VLM_OPERATION_SUCCESS",
                        transaction_id=transaction_id,
                    )

                case 501:  # Handle configuration request
                    normal_speed = message["Normal_Speed"]
                    approach_speed = message["Approach_Speed"]
                    steps_per_floor = message.get("Steps_Per_Floor", 0)
                    stop_pulse = message["Stop_Pulse"]
                    for_pulse = message["For_Pulse"]
                    back_pulse = message["Back_Pulse"]
                    collect_time = message["Collect_Time"]
                    return_time = message["Return_Time"]
                    hall_N_thresh = message["hall_N_thresh"]
                    hall_S_thresh = message["hall_S_thresh"]

                    db.VLM_Update_Configuration(
                        normal_speed,
                        approach_speed,
                        steps_per_floor,
                        stop_pulse,
                        for_pulse,
                        back_pulse,
                        collect_time,
                        return_time,
                        hall_N_thresh,
                        hall_S_thresh,
                    )
                case 603:  # Handle hall sensor reading
                    hall_value = message["hall_value"]
                    if message["transaction_id"] is None:
                        type = "AUTO_HALL_SENSOR_READING"
                    else:
                        type = "MANUAL_HALL_SENSOR_READING"
                    
                    db.log_event(
                        "INFO",
                        f"Hall sensor reading received: {hall_value}",
                        "ESP32",
                        transaction_type=type,
                        transaction_id=message["transaction_id"],
                    )
                case _:
                    print(f"Unhandled message: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        print("ESP32 disconnected")
        db.log_event(
            "WARNING",
            "ESP32 WebSocket Disconnected",
            "ESP32",
            transaction_type="WEBSOCKET_DISCONNECTION",
        )
        ws = None

def start_websocket_server():
    async def run_server():
        db.log_event(
            "INFO",
            "Starting WebSocket Server on port 8765",
            "Server",
            transaction_type="WEBSOCKET_SERVER_START",
        )
        print("Creating send_queued_messages task...")
        send_task = asyncio.create_task(send_queued_messages())
        print(f"Send task created: {send_task}")
        
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765) as server:
            # Run both tasks concurrently
            await asyncio.gather(
                server.serve_forever(),
                send_task,
                return_exceptions=True
            )
    
    asyncio.run(run_server())

def init_websocket_server():
    # Start WebSocket server in a thread
    global websocket_started
    if not websocket_started:
        thread = threading.Thread(target=start_websocket_server, daemon=True)
        thread.start()
        websocket_started = True


# Async version for use in async code
async def WS_Send(json_string):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, message_queue.put, json_string)
    print(f"Message queued for sending via WebSocket: {json_string}")
    return True

# Sync wrapper for use in sync code
def WS_Send_sync(json_string):
    message_queue.put(json_string)
    print(f"Message queued for sending via WebSocket (sync): {json_string} (queue_size={message_queue.qsize()})")
    return True

async def send_queued_messages():
    import sys
    print("=== SEND TASK STARTING ===", flush=True)
    sys.stdout.flush()
    print("Send task started", flush=True)
    print(f"Queue object: {message_queue}, initial size: {message_queue.qsize()}", flush=True)
    loop = asyncio.get_event_loop()
    iteration = 0
    while True:
        iteration += 1
        print(f"[Iteration {iteration}] Waiting for message (queue_size={message_queue.qsize()})...", flush=True)
        msg = await loop.run_in_executor(None, message_queue.get)
        print(f"Processing queued message: {msg} (queue_size={message_queue.qsize()})")
        try:
            # Check if websocket is open - try multiple ways for compatibility
            is_open = False
            if ws:
                # Try .open attribute (older websockets)
                if hasattr(ws, 'open'):
                    is_open = ws.open
                # Try .state for newer websockets library
                elif hasattr(ws, 'state'):
                    from websockets.protocol import State
                    is_open = ws.state == State.OPEN
                # Fallback: check if close_code is None (connection still active)
                elif hasattr(ws, 'close_code'):
                    is_open = ws.close_code is None
                else:
                    # Last resort: assume it's open if ws exists
                    is_open = True
            
            print(f"WS check: ws={ws is not None}, is_open={is_open}", flush=True)
            
            if ws and is_open:
                print(f"WebSocket is open, sending: {msg}")
                await ws.send(msg)
                print(f"Message sent successfully")
            else:
                print(f"WebSocket not open (ws={ws is not None}, is_open={is_open}), re-queueing message")
                await loop.run_in_executor(None, message_queue.put, msg)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Error sending message: {e}, re-queueing")
            await loop.run_in_executor(None, message_queue.put, msg)
            await asyncio.sleep(1)