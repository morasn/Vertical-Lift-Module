# WebSocket Messages Documentation

This document outlines all WebSocket messages exchanged between the Python Flask server and the ESP32 device. Messages are categorized by direction (Python to ESP32 or ESP32 to Python), with details on reason, timing, sender, and JSON structure including data types.

## Message Overview
- **Direction**: Indicates who sends the message.
- **Code**: Unique identifier for the message type.
- **Reason**: Why the message is sent.
- **When**: Timing or trigger for sending.
- **Sender**: The component sending the message.
- **JSON Contents**: Detailed structure with data types.

## Python to ESP32 Messages

### Code 100-109 Family: Normal Website Operation to VLM
#### Code 100: Dispense Command
- **Reason**: Instructs the ESP32 to perform a dispensing operation for multiple floors/products.
- **When**: Triggered when a user initiates a dispense action in the Flask app, after calculating floors and orders.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 100,           // int: Message code
    "Iter": 2,             // int: Number of floors (length of Floors array)
    "Floors": ["F01", "B02"], // array of strings: Floor identifiers (e.g., "F01" for Front 01)
    "OrdersPerFloor": [1, 2], // array of ints: Number of orders per floor
    "transaction_id":  // int: Unique transaction ID for tracking
  }
  ```

- **Follow-up Required**: Yes — ESP shall send code 200 on successful completion.
- **Follow-up Code**: 200 (Success Response) — this confirms to Python that the ESP performed the requested operation for code 100 and includes the transaction ID.

#### Code 101: Restock Command
- **Reason**: Instructs the ESP32 to perform a restocking operation for a specific floor.
- **When**: Triggered when a user initiates a restock action in the Flask app.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 101,           // int: Message code
    "Floor": ["F01"],        // list: Floor identifier (e.g., "F01")
    "transaction_id":  // int: Unique transaction ID for tracking
  }
  ```

- **Follow-up Required**: Yes — ESP sends code 200 when restock completes.
- **Follow-up Code**: 200 (Success Response)



#### Code 102: Reorder Shelves Command 
- **Reason**: Would instruct the ESP32 to reorder shelves between positions.
- **When**: Not implemented in Python code; placeholder for future use.
- **Sender**: Python Flask server (hypothetical).
- **JSON Contents** (based on ESP32 handler):
  ```json
  {
    "code": 102,           // int: Message code
    "Iter": 2,             // int: Number of reorder operations
    "move_from": ["F01", "B02"], // array of strings: Source floor identifiers
    "move_to": ["F02", "B03"],   // array of strings: Destination floor identifiers
    "transaction_id": 626262   // int: Unique transaction ID for tracking
  }
  ```

- **Follow-up Required**: Yes — ESP sends code 200 after reorder is performed by the ESP. If Python will ever send 102, expect a 200 ack.
- **Follow-up Code**: 200 (Success Response)


### Code 110-119: Serving VLM when operator uses it

#### Code 110: Authenticate Operator Provide Transaction ID for future messages
- **Reason**: Authenticates operator and allows ESP to request transaction ID for tracking.
- **When**: Sent when operator initiates interaction and scans RFID. Awaits code 120 from ESP32.
- **Sender**: Python server.
- **JSON Contents**:
  ```json
  {
	"code": 110,           // int: Message code
  "operator": "RFID123", // string: RFID UID of the operator
	"transaction_id": 12345 // int: Unique transaction ID for tracking
  "Authenticated": true/false // bool: Whether authentication succeeded
  }
  ```

- **Follow-up Required**: Yes — The ESP will acknowledge the authentication with a code 200 message to confirm it's ready to proceed.
- **Follow-up Code**: 200 (Success Response) — sent by the ESP after receiving a valid 110 message to confirm it has set up state for the new transaction.

### Family 500-599: Configuration Messages from Python to ESP32
#### Code 500: Update Configuration Parameters
- **Reason**: Sends updated configuration parameters to the ESP32.
- **When**: Sent when configuration parameters are changed in the Flask app.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 500,                   // int: Message code
    "normal_delay": 400,           // int: Normal delay in ms
    "approaching_delay": 1600,     // int: Approaching delay in ms
    "stop_pulse": 1100,            // int: Stop pulse duration in ms
    "for_pulse": 1700,             // int: Forward pulse duration in ms
    "back_pulse": 1500,            // int: Backward pulse duration in ms
    "collect_time": 600,           // int: Collect time in ms
    "return_time": 600             // int: Return time in ms
  }
  ``` 
- **Follow-up Required**: No — informational message; ESP may log or display these parameters but does not need to respond.


### Family 600-699: Manual Control of the Machine & Sensor Reading
#### Code 600: Manual Vertical Command
- **Reason**: Instructs the ESP32 to move the elevator vertically number of steps.
- **When**: Triggered when a user initiates a manual vertical move in the Flask app.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 600,           // int: Message code
    "steps": 5             // int: Number of steps to move (positive for up, negative for down)
  }
  ```
- **Follow-up Required**: Yes — ESP sends code 200 when movement completes.
- **Follow-up Code**: 200 (Success Response)

#### Code 601: Manual Horizontal Command
- **Reason**: Instructs the ESP32 to move the shelf horizontally number of steps.
- **When**: Triggered when a user initiates a manual horizontal move in the Flask app.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 601,           // int: Message code
    "mill_sec": 500             // int: Number of milliseconds to move
    "PWM_Freq": 1000          // int: PWM Frequency for motor control (forward and backward)
  }
  ```

#### Code 602: Hall Sensor Reading Command
- **Reason**: Requests hall sensor readings from the ESP32.
- **When**: Triggered when a user requests sensor data in the Flask app.
- **Sender**: Python Flask server (`VLM_Control.py` via `WS_Send`).
- **JSON Contents**:
  ```json
  {
    "code": 602           // int: Message code
  }
  ```
  
## ESP32 to Python Messages

### Family 120-139: VLM Operation Messages from ESP32
#### Code 120: Operator RFID Scanned
- **Reason**: Notifies the server that an operator's RFID has been scanned via keypad input.
- **When**: Sent immediately after RFID scan during keypad interaction (key 'A' pressed).
- **Sender**: ESP32 (`Numpad.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 120,           // int: Message code
    "operator": "RFID123", // string: Scanned RFID UID of the operator
    "AuthTrials": 1        // int: Number of authentication trials attempted
  }
  ```

- **Follow-up Required**: Yes — Server validates the supplied `operator` UID and either issues a transaction id and marks the operator authenticated or returns a failure.
- **Follow-up Code**: 110 on success (Python -> ESP) with `transaction_id`; 120 on authentication failure (Python -> ESP) — this mirrors how the server currently replies and lets the ESP know whether to proceed.

#### Code 121: Floor and Operator Info
- **Reason**: Provides floor selection and operator details after keypad input.
- **When**: Sent after side and level are selected via keypad.
- **Sender**: ESP32 (`Numpad.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 121,           // int: Message code
    "Floors": ["F01"],     // array of strings: Selected floor(s) (e.g., ["F01"])
    "operator": "RFID123"  // string: Operator RFID UID
  }
  ```

- **Follow-up Required**: No (not strictly required) — the server logs the floor selection and normally waits for operation (code 122) or other messages. Optionally, you can implement a 200 ack from Python to ESP if you want the ESP to confirm receipt. 
- **Recommended**: Accept both `Floors` (array) and `floor_selected` (single string) on server to increase robustness.

#### Code 122: Operation and UIDs
- **Reason**: Confirms the operation type and provides scanned product UIDs after actuation.
- **When**: Sent after operation selection ('C' or 'D') and DualCycle execution.
- **Sender**: ESP32 (`Numpad.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 122,           // int: Message code
    "operation": "D",      // string: Operation type ('D' for Dispense, 'R' for Restock)
    "UIDs": ["UID001", "UID002"] // array of strings: Scanned product RFID UIDs (empty if none)
  }
  ```

- **Follow-up Required**: No (internal processing on server) — upon receipt Python processes the received UIDs and updates the DB; Python does not currently reply with a WebSocket code. 
- **Recommended**: You may optionally send a 200 ack from Python to indicate successful DB processing. Also add `Floors` and `operator` fields to the 122 payload from ESP for a simpler, stateless server implementation (otherwise server relies on message ordering).  

#### Code 123: Automatic Restock UID Reading
- **Reason**: Sends automatically scanned UID during automatic restock operation.
- **When**: Sent when a product is scanned automatically during restock.
- **Sender**: ESP32 (`RFID.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 123,           // int: Message code
    "uid": "UID001" // string: Automatically scanned product RFID UID
  }
  ```

- **Follow-up Required**: No — Server processes the automatic-restock UID and then invokes `VLM.Auto_Restock_Shelf_Get(uid, operator_id, transaction_id)` to handle physical actuation and DB operations. Python does not return a special code by default.
- **Recommended**: Send back a 200 (Success) from Python after the operation is queued/processed, to make the flow explicit in logs/clients.
 - **Follow-up Required**: Yes — Python will process the auto-restock request and then issue a restock command back to the ESP (code 101) with the detected Floor.
 - **Follow-up Code**: 101 (Restock Command) — this is sent by Python to the ESP to instruct it to retrieve the specified shelf for restocking.
 - **Recommended**: After Python queues/sends the 101 restock command, the ESP will eventually perform the operation and respond with code 200 to confirm completion.

#### Code 130: Manual UID Reading
- **Reason**: Sends manually scanned UID when operator uses manual read function.
- **When**: Sent when operator presses 'B' to manually read an RFID.
- **Sender**: ESP32 (`Numpad.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 130,           // int: Message code
    "uid": "UID001" // string: Manually scanned product RFID UID
  }
  ```

Optional extra field when sector read is available (ESP reads MIFARE data blocks and converts to readable string):

```json
{
  "code": 130,
  "uid": "UID001",
  "sector_data": "HEX:0A0B...|ASCII:..Kg.."
}
```

- **Follow-up Required**: No — Python's handler simply prints the UID. You may, however, call `Products_Restock` or a backend endpoint from Python to act on the UID. Consider returning an explicit 200 ack from Python if you want the ESP UI or logs to indicate success.

- **Follow-up Required**: No — Python's handler simply prints the UID. You may, however, call `Products_Restock` or a backend endpoint from Python to act on the UID. Consider returning an explicit 200 ack from Python if you want the ESP UI or logs to indicate success.

### Family 200-299: Success Responses from ESP32
#### Code 200: Success Response
- **Reason**: Acknowledges successful completion of a command (e.g., dispense, restock, reorder).
- **When**: Sent after processing codes 100, 101, or 102 without errors.
- **Sender**: ESP32 (`WebSocketHandler.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 200,           // int: Message code
    "transaction_id": 9656513 // int: Transaction ID from the original request
  }
  ```

- **Follow-up Required**: No — 200 is a final success acknowledgement sent by the ESP (device side) when it completes Python-initiated operations (100, 101, 102, 110) and there is nothing else the Python server must send back in most flows.


### Family 500-599: Informational and Configuration Messages 
#### Code 501: Configuration Parameters
- **Reason**: Sends configuration parameters from ESP32 to Python upon connection.
- **When**: Sent immediately after WebSocket connection is established.
- **Sender**: ESP32 (`WebSocketHandler.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 501,                   // int: Message code
    "normal_delay": 375,           // int: Normal delay in ms
    "approaching_delay": 1500,     // int: Approaching delay in ms
    "stop_pulse": 1000,            // int: Stop pulse duration in ms
    "for_pulse": 1600,             // int: Forward pulse duration in ms
    "back_pulse": 1400,            // int: Backward pulse duration in
    "collect_time": 500,           // int: Collect time in ms
    "return_time": 500             // int: Return time in ms
  }
  ``` 
- **Follow-up Required**: No — informational message; Python may log or display these parameters but does not need to respond.

### Family 600-699: Sensor Readings from ESP32
#### Code 603: Hall Sensor Readings


## Error Codes 
### Family 400-499: Error Responses from both Python and ESP32

#### Code 401: Unauthorized Error
- **Reason**: Indicates that the operator is not registered on system.
- **When**: Sent when the ESP32 receives a request from an unauthorized operator.
- **Sender**: Python server.
- **JSON Contents**:
  ```json
  {
	"code": 401,           // int: Message code
	"transaction_id": 12345 // int: Unique transaction ID for tracking
  }
  ```

- **Follow-up Required**: No — 401 is a terminal error indicating unauthorized access; ESP should retry or prompt operator for reauthorization.

#### Code 404: Unknown Code Error
- **Reason**: Indicates an unrecognized message code was received.
- **When**: Sent when the ESP32 receives a code not in [100, 101, 102].
- **Sender**: ESP32 (`WebSocketHandler.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 404,           // int: Message code
    "transaction_id": null // string or null: Transaction ID if provided in request
  }
  ```

  - **Follow-up Required**: No — this is a terminal error for an unrecognized code; the sender should not expect any further messages for that transaction and should log or alert.

#### Code 406: JSON Parse Error
- **Reason**: Indicates failure to parse incoming JSON.
- **When**: Sent when `deserializeJson` fails on received message.
- **Sender**: ESP32 (`WebSocketHandler.cpp` via `sendMessage`).
- **JSON Contents**:
  ```json
  {
    "code": 406,           // int: Message code
    "text": "deserializeJson() failed: InvalidInput", // string: Error description
    "transaction_id": null // string or null: Transaction ID if provided in request
  }
  ```

  - **Follow-up Required**: No — this is terminal for that message; the sender should correct the payload format. The recipient may optionally send an error 401/404 or log the failure.

