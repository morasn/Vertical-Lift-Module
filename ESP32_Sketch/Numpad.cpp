#include "Numpad.h"

Keypad KeypadInit()
{

  char keys[ROW_NUM][COLUMN_NUM] = {
      {'1', '2', '3', 'A'},
      {'4', '5', '6', 'B'},
      {'7', '8', '9', 'C'},
      {'*', '0', '#', 'D'}};

  byte pin_rows[ROW_NUM] = {19, 18, 5, 17};    // GPIO19, GPIO18, GPIO5, GPIO17 connect to the row pins
  byte pin_column[COLUMN_NUM] = {16, 4, 0, 2}; // GPIO16, GPIO4, GPIO0, GPIO2 connect to the column pins

  Keypad keypad = Keypad(makeKeymap(keys), pin_rows, pin_column, ROW_NUM, COLUMN_NUM);
  return keypad;
}

void KeyPadInterpret()
{

  Keypad keypad = KeypadInit();
  char key = keypad.getKey();
  
  const unsigned long timeout = 60000;  // 30 seconds timeout

  if (key == 'A')
  {
    Serial.println(key);

    StaticJsonDocument<128> msg_json; // Allocate 256 bytes for response JSON

    AuthTrials = 0;
    String rfidOperator = "";

    unsigned long startTime = millis();  // Start timer

    while (!Authenticated && AuthTrials < 3 && (millis() - startTime) < timeout)
    {
      rfidOperator = "";


      while (rfidOperator == "")
      { // Wait for valid UID
        rfidOperator = RFID_SCAN_CHECK();
        delay(100);
      }


      msg_json["code"] = 120;
      msg_json["operator"] = rfidOperator;
      msg_json["AuthTrials"] = AuthTrials;
      sendMessage(msg_json);
      
      handleWebSocket();
      delay(100);
    }

    if (!Authenticated)
    {
      Serial.println("Authentication failed after 3 trials.");
      return; // Exit if not authenticated
    }

    char side = '\0'; // Initialize to null character
    
    startTime = millis();  // Start timer
    while (side == '\0' && (millis() - startTime) < timeout)
    { // Wait for valid input
      side = keypad.getKey();
      if (side != 'A' && side != 'B')
      {              // Check if valid (A or B)
        side = '\0'; // Reset if invalid
      }
      else if (side == 'A')
      {
        side = 'F'; // Front
      }
      else if (side == 'B')
      {
        side = 'B'; // Back
      }
      delay(100);
    }

    int level = -1; // Initialize to invalid value
    startTime = millis();  // Start timer

    while (level == -1 && (millis() - startTime) < timeout)
    { // Wait for valid level input
      char keyPressed = keypad.getKey();
      if (keyPressed)
      { // If a key was pressed
        if (keyPressed == 'C')
        {
          level = 10; // Special case for 'C'
        }
        else if (keyPressed >= '0' && keyPressed <= '9')
        {
          level = keyPressed - '0'; // Convert char digit to int
        }
        else
        {
          // Invalid key, ignore and continue waiting
          continue;
        }
        // Optional: Add range check if levels are limited (e.g., 0-10)
        if (level < 0 || level > 10)
        {             // Example: assume levels 0-10 are valid
          level = -1; // Reset if out of range
        }
      }
      delay(100);
    }

    String Floor[1]; // Array with one element
    if (level == 10)
    {
      Floor[0] = String(side) + String(level);
    }
    else
    {
      Floor[0] = String(side) + "0" + String(level);
    }

    msg_json["code"] = 121;
    JsonArray FloorsArray = msg_json.createNestedArray("Floors");
    FloorsArray.add(Floor[0]);
    msg_json["operator"] = rfidOperator;
    sendMessage(msg_json);

    char operation = '\0'; // Initialize to null character
    
    startTime = millis();  // Start timer

    while (operation == '\0' && (millis() - startTime) < timeout)
    { // Wait for valid input
      operation = keypad.getKey();
      if (operation != 'C' && operation != 'D')
      {                   // Check if valid (C or D)
        operation = '\0'; // Reset if invalid
      }
      else if (operation == 'C')
      {
        operation = 'R'; // Stop
      }
      delay(100);
    }

    int OrdersPerFloor[1] = {1};
    String *uids = DualCycle(1, Floor, OrdersPerFloor, true, 10);
    msg_json["code"] = 122;
    msg_json["operation"] = String(operation); // Convert char to String for ArduinoJson compatibility

    JsonArray uidArray = msg_json.createNestedArray("UIDs");
    
    for (int i = 0; i < 10; i++)
    {
      if (uids[i] != "")
      {
        uidArray.add(uids[i]);
      }
    }
    sendMessage(msg_json);
    Authenticated = false;
  }
}