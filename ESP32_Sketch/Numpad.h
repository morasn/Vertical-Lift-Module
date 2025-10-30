#ifndef NUMPAD_H
#define NUMPAD_H

// Keypad Activation
#define ROW_NUM 4	 // four rows
#define COLUMN_NUM 4 // four columns

#include <Keypad.h>
#include "RFID.h"
#include "WebSocketHandler.h"

extern bool Authenticated;
extern int AuthTrials;
extern int VLMtranscationID;

void KeyPadInterpret();

#endif
