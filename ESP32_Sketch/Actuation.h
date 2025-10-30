#ifndef ACTUATION_H
#define ACTUATION_H

#include <Arduino.h>
#include <ESP32Servo.h>
#include "RFID.h"

#pragma once

extern const int HallSensor;
extern const String Loading_Bay;
extern const String Buffer_Bay;

extern MFRC522 mfrc522;
extern int current_floor;

// Expose initialization and major functions
void initActuation(const int liftPin, const int drawerPin);
void CalibrateLift(const int SensorPin);
String* DualCycle(const int iterations, String floors[], int OrdersPerFloor[], bool returnUIDs, int maxUIDs);
void ReorderShelves(const String move_from[], const String move_to[], const int num_iter);
void ProductRestock(const String Floor);

#endif
