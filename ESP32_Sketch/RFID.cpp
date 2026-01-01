#include "RFID.h"
#include "OLED.h"

#define TNF_WELL_KNOWN 0x01

// Forward declaration
String parseNDEFText(String hexData);

// Static variable to track last successful read time
static unsigned long lastReadTime = 0;
static const unsigned long READ_COOLDOWN = 2000;  // 2 seconds between reads

String RFID_SCAN_CHECK() {
  // Cooldown check - don't try to read too frequently
  if (millis() - lastReadTime < READ_COOLDOWN) {
    return "";
  }

  // Reset the loop if no new card present on the sensor/reader
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return "";
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    Serial.println("Failed to read card serial");
    return "";
  }

  // Update last read time immediately to prevent re-entry
  lastReadTime = millis();

  // Debug: Print card details
  Serial.print("Card UID: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  Serial.print("Card SAK: ");
  Serial.println(mfrc522.uid.sak, HEX);

  Serial.print("Card type: ");
  MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
  Serial.println(mfrc522.PICC_GetTypeName(piccType));

  // Check if this is actually a MIFARE Classic card
  if (piccType != MFRC522::PICC_TYPE_MIFARE_1K && piccType != MFRC522::PICC_TYPE_MIFARE_4K) {
    Serial.println("ERROR: This is not a MIFARE Classic card!");
    Serial.println("Card type not supported by this code.");
    mfrc522.PICC_HaltA();
    return "";
  }

  // Increase antenna gain for better communication
  mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);

  // Give the card time to stabilize after being detected
  delay(50);

  String allData = "";
  byte buffer[18];
  byte size = sizeof(buffer);

  // Key order - try most common keys for sector 1
  byte keys[][6] = {
    { 0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7 },  // MAD key - most common for sector 1
    { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF },  // Default factory
    { 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5 },  // Custom key
    { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 },  // All zeros
  };
  int numKeys = sizeof(keys) / sizeof(keys[0]);

  // ONLY READ SECTOR 1 - contains all the NDEF data we need
  int sector = 1;
  byte firstBlock = sector * 4;  // Block 4
  bool authed = false;
  MFRC522::StatusCode status;

  // Try to authenticate sector 1 with most likely keys
  for (int k = 0; k < numKeys && !authed; k++) {
    // Load the key
    for (byte i = 0; i < 6; i++) {
      key.keyByte[i] = keys[k][i];
    }

    // Try Key A
    status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A,
                                      firstBlock, &key, &(mfrc522.uid));
    if (status == MFRC522::STATUS_OK) {
      authed = true;
      Serial.print("✓ Sector 1 authenticated with Key A: ");
      for (byte i = 0; i < 6; i++) {
        if (keys[k][i] < 0x10) Serial.print("0");
        Serial.print(keys[k][i], HEX);
      }
      Serial.println();
      break;
    }

    // Try Key B
    status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_B,
                                      firstBlock, &key, &(mfrc522.uid));
    if (status == MFRC522::STATUS_OK) {
      authed = true;
      Serial.print("✓ Sector 1 authenticated with Key B: ");
      for (byte i = 0; i < 6; i++) {
        if (keys[k][i] < 0x10) Serial.print("0");
        Serial.print(keys[k][i], HEX);
      }
      Serial.println();
      break;
    }

    mfrc522.PCD_StopCrypto1();
  }

  if (!authed) {
    Serial.print("✗ Sector 1 authentication failed: ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return "";
  }

  // Successfully authenticated sector 1 - read all 3 data blocks
  for (byte b = 0; b < 3; b++) {
    byte block = firstBlock + b;
    size = sizeof(buffer);

    status = mfrc522.MIFARE_Read(block, buffer, &size);
    if (status != MFRC522::STATUS_OK) {
      Serial.print("Read failed for block ");
      Serial.print(block);
      Serial.print(": ");
      Serial.println(mfrc522.GetStatusCodeName(status));
      break;
    }

    // Convert to hex string
    for (byte i = 0; i < 16; i++) {
      if (buffer[i] < 0x10) allData += "0";
      allData += String(buffer[i], HEX);
    }

    delay(10);  // Small delay between blocks
  }

  // Halt the card and clean up
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  if (allData.length() > 0) {
    Serial.print("Successfully read sector 1, data length: ");
    Serial.println(allData.length());
    Serial.println("Data: " + allData.substring(0, min(100, (int)allData.length())) + "...");
  } else {
    Serial.println("No data read from sector 1");
  }

  return allData;
}

// Parse NDEF Text Record from hex string
String parseNDEFText(String hexData) {
  // Convert hex string to bytes
  int len = hexData.length() / 2;
  if (len == 0) return "";

  byte data[len];
  for (int i = 0; i < len; i++) {
    String byteStr = hexData.substring(i * 2, i * 2 + 2);
    data[i] = (byte)strtol(byteStr.c_str(), NULL, 16);
  }

  // Look for NDEF Text Record (TNF=0x01, Type="T")
  // NDEF format: [TLV][NDEF Message][NDEF Record]

  // Find the start of NDEF message (look for 0x03 TLV tag)
  int ndefStart = -1;
  for (int i = 0; i < len - 5; i++) {
    if (data[i] == 0x03) {  // TLV tag for NDEF Message
      ndefStart = i + 2;    // Skip tag and length byte
      break;
    }
  }

  if (ndefStart == -1) {
    Serial.println("No NDEF message found");
    return "";
  }

  // Parse NDEF Record Header
  byte header = data[ndefStart];
  bool mb = (header & 0x80) != 0;  // Message Begin
  bool me = (header & 0x40) != 0;  // Message End
  bool sr = (header & 0x10) != 0;  // Short Record
  byte tnf = header & 0x07;        // Type Name Format

  int pos = ndefStart + 1;
  byte typeLength = data[pos++];

  byte payloadLength = 0;
  if (sr) {
    payloadLength = data[pos++];  // Short record = 1 byte length
  } else {
    // Long record = 4 bytes length (not common for text)
    payloadLength = (data[pos++] << 24) | (data[pos++] << 16) | (data[pos++] << 8) | data[pos++];
  }

  // Check if it's a Text Record (Type = "T")
  if (typeLength == 1 && data[pos] == 'T') {
    pos++;  // Skip type

    // Text Record Payload Structure:
    // [Status byte][Language code...][Text...]
    byte statusByte = data[pos++];
    byte langCodeLen = statusByte & 0x3F;  // Lower 6 bits

    // Skip language code
    pos += langCodeLen;

    // Extract text
    int textLen = payloadLength - 1 - langCodeLen;
    String text = "";
    for (int i = 0; i < textLen && pos < len; i++) {
      text += (char)data[pos++];
    }

    Serial.print("Parsed NDEF Text: ");
    Serial.println(text);
    return text;
  }

  Serial.println("Not a Text Record");
  return "";
}

// Unified function to get parsed RFID text data
String getRFIDTextData() {
  String sectorData = RFID_SCAN_CHECK();
  if (sectorData == "") return "";
  return parseNDEFText(sectorData);
}

// void RFID_Send(){
//     String sectorData = RFID_SCAN_CHECK();
//     if (sectorData == "") return; // don't send empty reads

//     displayMessage("RFID scanned");

//     // Parse NDEF text from the hex data
//     String ndefText = parseNDEFText(sectorData);

//     StaticJsonDocument<1024> msg_json;
//     msg_json.clear();
//     msg_json["code"] = 130;
//     msg_json["sector_data"] = sectorData;
//     msg_json["uid"] = ndefText; // Add parsed text

//     sendMessage(msg_json);
// }