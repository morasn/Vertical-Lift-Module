import asyncio
# import queue
import websockets
import threading
import json

import DB.DB_Back as db
import Backend
# Global to store connected ESP32 WebSocket
ws = None

message_queue = asyncio.Queue()

async def websocket_handler(websocket, path):
    global ws
    ws = websocket
    print("ESP32 connected")
    send_task = asyncio.create_task(send_queued_messages(ws))

    try:
        async for message in websocket:
            print(f"Received from ESP32: {message}")
            message = json.loads(message)
            match int(message["code"]):
                case 120:  # Handle authentication request from ESP32 and provide transaction ID

                    transaction_id = db.Transaction_ID_Generator()
                    operator_info = db.Operator_ID_Query(message["operator"])

                    if operator_info:
                        # Send the transaction ID and operator info back to the ESP32
                        response = {
                            "code": 120,
                            "transaction_id": transaction_id,
                        }

                        db.log_event(
                            "INFO",
                            "Operator Authenticated & Transaction Created",
                            transaction_type="AUTHENTICATION",
                            transaction_id=transaction_id,
                        )
                        await websocket.send(json.dumps(response))
                    else:

                        db.log_event(
                            "ERROR",
                            "Authentication Failed: Invalid Operator ID",
                            transaction_type="AUTHENTICATION",
                            transaction_id=transaction_id,
                        )
                        await websocket.send(
                            json.dumps({"code": 401, "message": "Invalid operator ID"})
                        )
                case 121:  # Handle floor selection and operator info
                    transaction_id = message["transaction_id"]
                    floor_selected = message["floor_selected"]
                    operator_id = message["operator"]

                    db.log_event(
                        "INFO",
                        f"Floor {floor_selected} selected by Operator {operator_id}",
                        transaction_type="FLOOR_SELECTION",
                        transaction_id=transaction_id,
                    )
                case 122: # handle UIDs sent from ESP32
                    transaction_id = message["transaction_id"]
                    uid_list = message["UIDs"]
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
                        transaction_type="UID_PROCESSING",
                        transaction_id=transaction_id,
                    )
                    Backend.Norm_Product_Operation(transaction_id, shelf_pos, uid_list, QTY, message["operator_id"], Source="ESP32", project=None)

                case _:
                    print(f"Unhandled message: {message}")
    
    except websockets.exceptions.ConnectionClosed:
        print("ESP32 disconnected")
        ws = None
    finally:
        send_task.cancel()

def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(websocket_handler, "0.0.0.0", 8765)  # Listen on port 8765
    loop.run_until_complete(server)
    loop.run_forever()


def init_websocket_server():
    # Start WebSocket server in a thread
    thread = threading.Thread(target=start_websocket_server, daemon=True)
    thread.start()


# Async version for use in async code
async def WS_Send(json_string):
    await message_queue.put(json_string)
    return True

# Sync wrapper for use in sync code
def WS_Send_sync(json_string):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.run_coroutine_threadsafe(message_queue.put(json_string), loop)
    else:
        loop.run_until_complete(message_queue.put(json_string))
    return True

async def send_queued_messages(websocket):
    while True:
        json_string = await message_queue.get()
        await websocket.send(json_string)
