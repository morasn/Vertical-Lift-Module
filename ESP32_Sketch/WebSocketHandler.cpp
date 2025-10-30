#include "WebSocketHandler.h"

WebSocketsClient webSocket;

bool Authenticated = false;
int AuthTrials = 0;
int VLMtranscationID = 0;

// Initialize WiFi connection
void initWiFi(const char *ssid, const char *password)
{
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// Callback function when a message is received
void webSocketEvent(WStype_t type, uint8_t *payload, size_t length)
{
  switch (type)
  {
  case WStype_DISCONNECTED:
    Serial.println("[WebSocket] Disconnected!");
    break;
  case WStype_CONNECTED:
    Serial.println("[WebSocket] Connected to server");
    webSocket.sendTXT("Hello from Arduino!");
    break;
  case WStype_TEXT:
    Serial.printf("[WebSocket] Received: %s\n", payload);

    StaticJsonDocument<256> dict;     // Allocate 512 bytes for incoming JSON
    StaticJsonDocument<128> msg_json; // Allocate 256 bytes for response JSON

    // Deserialize the JSON document
    DeserializationError error = deserializeJson(dict, payload);

    // Test if parsing succeeds.
    if (error)
    {
      Serial.print(F("deserializeJson() failed: "));
      Serial.println(error.f_str());

      msg_json["code"] = 406;
      msg_json["text"] = error.f_str();

      sendMessage(msg_json);
      return;
    }

    msg_json["transaction_id"] = dict["transaction_id"];

    switch (dict["code"].as<int>())
    {
    case 100:
    { // Project
      const int Iter = dict["Iter"];
      String Floors[Iter]; // assuming max 10
      int OrdersPerFloor[Iter];
      JsonArray arr = dict["Floors"];
      JsonArray arr2 = dict["OrdersPerFloor"];
      for (int i = 0; i < Iter; i++)
      {
        Floors[i] = String(arr[i]);
        OrdersPerFloor[i] = OrdersPerFloor[i];
      }

      DualCycle(Iter, Floors, OrdersPerFloor, false, 10);

      msg_json["code"] = 200;
      sendMessage(msg_json);

      break;
    }
    case 101:
    { // Product Restock
      String Floor = dict["Floor"];

      ProductRestock(Floor);

      msg_json["code"] = 200;
      sendMessage(msg_json);

      break;
    }
    case 102: // Reorder Shelves
    {
      const int Iter = dict["Iter"];
      String move_from[Iter];
      String move_to[Iter];
      JsonArray arr = dict["move_from"];
      JsonArray arr2 = dict["move_to"];
      for (int i = 0; i < Iter; i++)
      {
        move_from[i] = String(arr[i]);
        move_to[i] = String(arr2[i]);
      }

      ReorderShelves(move_from, move_to, Iter);

      msg_json["code"] = 200;
      sendMessage(msg_json);

      break;
    }

    case 110:
    { // VLM Operator Authenticated {}
      String operator_id = dict["operator_id"];
      VLMtranscationID = dict["transaction_id"];

      Authenticated = true;

      msg_json["code"] = 200;
      msg_json["transaction_id"] = VLMtranscationID;

      sendMessage(msg_json);

      break;
    }

    case 120:
    { // VLM Operator Deauthenticated {}

      VLMtranscationID = int(dict["transaction_id"]);

      Authenticated = false;
      AuthTrials++;

      msg_json["code"] = 200;
      msg_json["transaction_id"] = VLMtranscationID;

      sendMessage(msg_json);

      break;
    }

    default:
      msg_json["code"] = 404;

      sendMessage(msg_json);
    }
  }
}

void initWebSocket(const char *serverUrl)
{
  webSocket.begin(serverUrl, 80, "/"); // Example: ws://192.168.1.100:5000/ws
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000); // auto reconnect every 5s if disconnected
}

void handleWebSocket()
{
  webSocket.loop();
}

void sendMessage(JsonDocument msg_json)
{
  String msg;
  serializeJson(msg_json, msg);

  webSocket.sendTXT(msg);
}
