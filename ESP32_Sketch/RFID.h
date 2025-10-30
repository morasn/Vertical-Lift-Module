#ifndef RFID_H
#define RFID_H

#include <SPI.h>
#include <MFRC522.h>

extern MFRC522 mfrc522;


String RFID_SCAN_CHECK();

#endif
