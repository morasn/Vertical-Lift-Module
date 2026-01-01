#include "Numpad.h"
#include "OLED.h"

#define I2C_ADDR 0x20

char keymapFlat[] = "123A456B789C*0#DNF";

extern TwoWire I2CExtender;
I2CKeyPad keypad(I2C_ADDR, &I2CExtender);

void KeypadInit() {
  bool begin_ok = keypad.begin();
  keypad.loadKeyMap(keymapFlat);
  Serial.print("Keypad begin OK: ");
  Serial.println(begin_ok);
  Serial.print("Keypad isConnected: ");
  Serial.println(keypad.isConnected());
  Serial.print("Keypad isPressed (init): ");
  Serial.println(keypad.isPressed());
  // Quick I2C scan on the extender bus for debugging
  Serial.println("I2C Extender scan:");
  for (uint8_t addr = 1; addr < 127; ++addr) {
    I2CExtender.beginTransmission(addr);
    uint8_t err = I2CExtender.endTransmission();
    if (err == 0) {
      Serial.print(" - Found device at 0x"); Serial.println(addr, HEX);
    }
  }
  // Optional self-test: print any key presses for 5 seconds on startup
  unsigned long testStart = millis();
  Serial.println("Keypad self-test: press keys now...");
  while (millis() - testStart < 5000) {
    if (keypad.isPressed()) {
      int idx = keypad.getLastKey();
      char ch = keypad.getChar();
      Serial.print("SELFTEST - idx: "); Serial.print(idx);
      Serial.print(" ch: "); Serial.println(ch);
    }
    delay(10);
  }
  // nothing to return; keypad is global
}


// Use reference to avoid copying the Keypad object and to operate on the
// instance created in the main sketch (this supports "keypad buddy" setups).
// Helper functions to clarify intent and reduce code duplication
static const unsigned long kDefaultTimeoutMs = 30000UL; // default keypad timeout

// Wait for a valid RFID UID and return it (or an empty string on timeout)
static String waitForRFID(unsigned long timeoutMs) {
  unsigned long start = millis();
  String uid = "";
  while ((millis() - start) < timeoutMs && uid == "") {
    uid = getRFIDTextData();
    // Process websocket events while waiting so responses can arrive
    handleWebSocket();
    delay(100);
  }
  return uid;
}

// Wait for a key that is in the validKeys string. Returns '\0' on timeout.
static char waitForValidKey(I2CKeyPad &keypad, const char *validKeys, unsigned long timeoutMs) {
  unsigned long start = millis();
  while ((millis() - start) < timeoutMs) {
    char k = keypad.getChar();
    
    if (k != '\0' || k != 'N' ) {
      Serial.print("Key pressed: ");
      Serial.println(k);
      
      // Check membership in validKeys
      for (const char *p = validKeys; *p != '\0'; ++p) {
        if (*p == k) return k;
      }
    }
    delay(100);
  }
  return '\0';
}

// Wait for a level entry. Returns -1 on timeout, 0..10 for levels (10 when 'C' used as special)
static int waitForLevel(I2CKeyPad &keypad, unsigned long timeoutMs) {
  unsigned long start = millis();
  while ((millis() - start) < timeoutMs) {
    char k = keypad.getChar();
    if (k != '\0' || k != 'N') {
      if (k >= '1' && k <= '7') return (k - '0');
    }
    delay(100);
  }
  return -1; // timeout/failure
}

// Build floor string like "F01" or "B10"
static String buildFloorString(char side, int level) {
  char buffer[5];
  if (level == 10) {
    snprintf(buffer, sizeof(buffer), "%c%d", side, level);
  } else {
    snprintf(buffer, sizeof(buffer), "%c%02d", side, level); // e.g. F01
  }
  return String(buffer);
}

void KeyPadInterpret(I2CKeyPad &keypad) {
  char order = keypad.getChar();
  if (order == '\0' || order =='N')  return; // Only act if a key is pressed

  Serial.print("Keypad Input: ");
  Serial.println(order);
  
  JsonDocument msg_json;

  // Only respond when 'A' or 'B' are pressed
  if (order != 'A' && order != 'B') return;

  Serial.println(order);

  AuthTrials = 0;

  displayMessage("Scan your Operator ID:");

  // 1) Authenticate operator
  String operatorId = "";
  
  unsigned long authStart = millis();
  while (!Authenticated && AuthTrials < 3 && (millis() - authStart) < kDefaultTimeoutMs) {
    
    operatorId = waitForRFID(kDefaultTimeoutMs);
    // Inform server of an authentication attempt
    // Sanitize the operatorId; if it begins with a 2-char prefix and a colon (e.g. "ID:123"), strip the prefix
    if (operatorId.length() > 3 && operatorId.charAt(2) == ':') {
      operatorId = operatorId.substring(3);
    } else {
      // Remove any leading non-alnum characters
      int idx = 0;
      while (idx < operatorId.length() && !isAlphaNumeric(operatorId.charAt(idx))) idx++;
      if (idx > 0) operatorId = operatorId.substring(idx);
    }
    operatorId.trim();
    Serial.print("Prepared operatorId for auth: "); Serial.println(operatorId);
    if (operatorId == "") {
      Serial.println("Empty operator read; waiting for next scan...");
      continue; // go back to waiting for RFID
    }
    msg_json["code"] = 120;
    msg_json["operator"] = operatorId;
    msg_json["AuthTrials"] = AuthTrials;
    
    sendMessage(msg_json);
    // Actively process websocket messages while waiting for auth outcome
    for (int pump = 0; pump < 10 && !Authenticated && AuthTrials == 0; ++pump) {
      handleWebSocket();
      delay(100);
    }
  }

  if (!Authenticated) {
    Serial.println("Authentication failed after 3 trials.");
    displayMessage("Timeout / Auth failed");
    delay(2000);
    HomeMessage();
    return;
  }

  displayMessage("Authenticated!");
  delay(1000);

  if (order == 'A') {
    // 2) Choose side (front/back)
    displayMessage("Side: A=Front B=Back");
    char sideKey = waitForValidKey(keypad, "AB", kDefaultTimeoutMs);
    if (sideKey == '\0') {
      displayMessage("Timeout");
      HomeMessage();
      Authenticated = false;
      return; // timeout
    }
    char side = (sideKey == 'A') ? 'F' : 'B';

    // 3) Choose level 0..10
    displayMessage("Enter Level: 1-7");
    int level = waitForLevel(keypad, kDefaultTimeoutMs);
    if (level < 0) {
      displayMessage("Timeout / Incorrect level");
      delay(1000);
      HomeMessage();
      return; // timeout
    }

    // Prepare and send selected floor
    String floorStr = buildFloorString(side, level);
    
    
    msg_json["code"] = 121;
    JsonArray floors = msg_json.createNestedArray("Floors");
    floors.add(floorStr);
    msg_json["operator"] = operatorId;
    msg_json["transaction_id"] = VLMtransactionID;
    sendMessage(msg_json);

    // 4) Choose operation (C/D -> R/Stop or continue)
    displayMessage("Select: C=Restock D=Dispense");
    char opKey = waitForValidKey(keypad, "CD", kDefaultTimeoutMs);
    if (opKey == '\0') {
      displayMessage("Timeout / No operation");
      delay(1000);
      HomeMessage();

      return; // timeout
    }
    char operation = (opKey == 'C') ? 'R' : opKey; // 'C' -> 'R' (stop), otherwise pass through

    // 5) Run DualCycle and send UIDs back
    int ordersPerFloor[1] = {1};
    String floorArr[1] = {floorStr};
    String *uids = DualCycle(1, floorArr, ordersPerFloor, true, 10);

    
    msg_json["code"] = 122;
    msg_json["operation"] = String(operation);
    JsonArray uidArray = msg_json.createNestedArray("UIDs");
    for (int i = 0; i < 10; ++i) {
      if (uids[i] != "") uidArray.add(uids[i]);
    }
    sendMessage(msg_json);
    Authenticated = false; // reset auth after operation
  } else {
    // order == 'B' : Auto restock / manual probe path
    displayMessage("Scan product RFID");
    String uid = waitForRFID(kDefaultTimeoutMs);
    if (uid == "") {
      displayMessage("Timeout / No UID");
      delay(1000);
      HomeMessage();
      return; // timeout
    }

    Serial.print("Manual UID Reading: ");
    Serial.println(uid);

    msg_json["code"] = 123;
    msg_json["uid"] = uid;
    msg_json["operator"] = operatorId;
    msg_json["transaction_id"] = VLMtransactionID;
    sendMessage(msg_json);

    while (AutoRestocked == false) {
      handleWebSocket();
      delay(100);
    }
    AutoRestocked = false; 
  }
}