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

## Code 100-109 Family: Normal Website Operation to VLM
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



#### Code 102: Reorder Shelves Command (Handled but not sent in provided code)
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


### Code 110-119: Serving VLM when operator uses it

#### Code 110: Authenticate Operator Provide Transaction ID for future messages
- **Reason**: Authenticates operator and allows ESP to request transaction ID for tracking.
- **When**: Sent when operator initiates interaction and scans RFID. Awaits code 120 from ESP32.
- **Sender**: Python server.
- **JSON Contents**:
  ```json
  {
	"code": 110,           // int: Message code
	"transaction_id": 12345 // int: Unique transaction ID for tracking
  }
  ```


## ESP32 to Python Messages


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

## Notes
- **Missing Messages**: Code 102 is handled by ESP32 but not sent by Python in the provided code—documented hypothetically.
- **Data Types**: All fields are explicitly typed (e.g., int, string, array). Arrays are of strings or ints as specified.
- **Transaction IDs**: Used for tracking and included in responses where applicable.
- **Direction**: All messages are bidirectional, but categorized by sender.
- **Updates**: This documentation is based on the provided code; update if new messages are added.