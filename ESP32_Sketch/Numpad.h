#ifndef NUMPAD_H
#define NUMPAD_H

// Keypad Activation
#define ROW_NUM 4	 // four rows
#define COLUMN_NUM 4 // four columns

#include <I2CKeyPad.h>
#include "RFID.h"
#include "WebSocketHandler.h"
#include <PCF8574.h>

extern I2CKeyPad keypad;

extern bool Authenticated;
extern int8_t AuthTrials;
extern int VLMtransactionID;
extern bool AutoRestocked;
extern PCF8574 pcf8574;
extern I2CKeyPad keypad;

// I2CKeyPad& KeypadInit();
void KeypadInit();
void KeyPadInterpret(I2CKeyPad &keypad);

#endif
