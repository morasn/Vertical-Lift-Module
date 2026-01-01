#ifndef RFID_H
#define RFID_H

#include <SPI.h>
#include <MFRC522.h>
#include <NfcAdapter.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include "WebSocketHandler.h"
#include <vector>

extern MFRC522 mfrc522;
extern MFRC522::MIFARE_Key key;


// String RFID_SCAN_CHECK();
String getRFIDTextData();
// void RFID_Send();

#endif
