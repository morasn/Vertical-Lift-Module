#include "WebSocketHandler.h"

WebSocketsClient webSocket;

bool Authenticated = false;
int8_t AuthTrials = 0;
int VLMtransactionID = 0;
bool AutoRestocked = false;

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
  displayMessage("WiFi connected");
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
    {
      // webSocket.sendTXT("Hello from ESP32!");
      JsonDocument msg_json; // response JSON
      msg_json["code"] = 501;
      msg_json["Normal_Speed"] = preferences.getInt("Normal_Speed", 2720);
      msg_json["Approach_Speed"] = preferences.getInt("Approach_Speed", 1600);
      msg_json["Steps_Per_Floor"] = preferences.getInt("Steps_Per_Floor", 1273);
      msg_json["Stop_Pulse"] = preferences.getInt("Stop_Pulse", 1500);
      msg_json["For_Pulse"] = preferences.getInt("For_Pulse", 1600);
      msg_json["Back_Pulse"] = preferences.getInt("Back_Pulse", 1400);
      msg_json["Collect_Time"] = preferences.getInt("Collect_Time", 2000);
      msg_json["Return_Time"] = preferences.getInt("Return_Time", 2000);
      msg_json["hall_N_thresh"] = preferences.getInt("hall_N_thresh", 2000);
      msg_json["hall_S_thresh"] = preferences.getInt("hall_S_thresh", 2000);
      sendMessage(msg_json);
    }
    break;
  case WStype_TEXT:
    Serial.printf("[WebSocket] Received: %s\n", payload);

    {
      JsonDocument dict;     // incoming JSON
      JsonDocument msg_json; // response JSON

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
      displayMessage("Dispensing project");
      const int Iter = dict["Iter"];
      String Floors[Iter]; // assuming max 10
      int OrdersPerFloor[Iter];
      JsonArray arr = dict["Floors"];
      JsonArray arr2 = dict["OrdersPerFloor"];
      for (int i = 0; i < Iter; i++)
      {
        Floors[i] = String(arr[i]);
        OrdersPerFloor[i] = arr2[i];
      }

      DualCycle(Iter, Floors, OrdersPerFloor, false, 10);

      msg_json["code"] = 200;
      msg_json["msg"] = "Project dispensed";
      msg_json["transaction_id"] = dict["transaction_id"];
      sendMessage(msg_json);

      break;
    }
    case 101:
    { // Product Restock
      String Floor = dict["Floor"];
      displayMessage("Restocking " + Floor);

      ProductRestock(Floor);

      msg_json["code"] = 200;
      msg_json["msg"] = "Restock complete";
      msg_json["transaction_id"] = dict["transaction_id"];
      sendMessage(msg_json);
      
      AutoRestocked = true;
      break;
    }
    case 102: // Reorder Shelves
    {
      displayMessage("Reordering shelves");
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
      msg_json["msg"] = "Reordering complete";
      // msg_json["transaction_id"] = dict["transaction_id"];
      sendMessage(msg_json);

      break;
    }

    case 110:
    { // VLM Operator Authenticated {}
      if (dict["Authenticated"] == false)
      {
        VLMtransactionID = dict["transaction_id"].as<int>();
        Authenticated = false;
        AuthTrials++;

        displayMessage("Auth failed");

        msg_json["code"] = 200;
        msg_json["msg"] = "Auth failed";
        msg_json["transaction_id"] = VLMtransactionID;

        sendMessage(msg_json);
      }
      else
      {
        String operator_id = dict["operator_id"].as<const char*>();
        VLMtransactionID = dict["transaction_id"].as<int>();

        Authenticated = true;
        AuthTrials = 0;
        displayMessage("Authenticated");

        msg_json["code"] = 200;
        msg_json["msg"] = "Auth successful";
        msg_json["transaction_id"] = VLMtransactionID;

        sendMessage(msg_json); 
      }
      break;
    }

    case 500: // change default motor values
    {
      preferences.begin("operation", false);
      preferences.putInt("Normal_Speed", dict["Normal_Speed"]);
      preferences.putInt("Approach_Speed", dict["Approach_Speed"]);
      preferences.putInt("Steps_Per_Floor", dict["Steps_Per_Floor"]);
      preferences.putInt("Stop_Pulse", dict["Stop_Pulse"]);
      preferences.putInt("For_Pulse", dict["For_Pulse"]);
      preferences.putInt("Back_Pulse", dict["Back_Pulse"]);
      preferences.putInt("Collect_Time", dict["Collect_Time"]);
      preferences.putInt("Return_Time", dict["Return_Time"]);
      preferences.putInt("hall_N_thresh", dict["hall_N_thresh"]);
      preferences.putInt("hall_S_thresh", dict["hall_S_thresh"]);
      preferences.end();

      msg_json["code"] = 200;
      msg_json["msg"] = "Settings updated";
      sendMessage(msg_json);
      break;
    }

    case 600: // vertical lift motion
    {
      int steps = dict["steps"];
      bool direction = dict["direction"];
      long transaction_id = dict["transaction_id"];
      ManualVerticalMotion(steps, direction);
      

      msg_json["code"] = 200;
      msg_json["msg"] = "Manual vertical motion complete";
      msg_json["transaction_id"] = transaction_id;
      sendMessage(msg_json); 
      break;
    }
    case 601: // horizontal drawer motion
    {
      int duration_ms = dict["duration_ms"];
      int left_pwm_freq = dict["left_pwm_freq"];
      int right_pwm_freq = dict["right_pwm_freq"];
      int transaction_id = dict["transaction_id"];

      ManualHorizontalMotion(duration_ms, left_pwm_freq, right_pwm_freq );

      msg_json["code"] = 200;
      msg_json["msg"] = "Manual horizontal motion complete";
      msg_json["transaction_id"] = transaction_id;
      sendMessage(msg_json);
      break; 
    }
    case 602: // immediate hall sensor read
    {
      int transaction_id = dict["transaction_id"];
      pinMode(HallSensor, INPUT); // Ensure correct mode
      int hall_value = analogRead(HallSensor);

      msg_json["code"] = 603;
      msg_json["transaction_id"] = transaction_id;
      msg_json["hall_value"] = hall_value;
      msg_json["hall_pin"] = HallSensor;
      sendMessage(msg_json);
      break;
    }
    default:
      msg_json["code"] = 404;

      sendMessage(msg_json);
    }
    }
  }
}

void initWebSocket(const char *serverUrl, const int port)
{
  webSocket.begin(serverUrl, port, "/ws"); // Example: ws://192.168.1.100:5000/ws
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000); // auto reconnect every 5s if disconnected
  displayMessage("WS initialized");

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
