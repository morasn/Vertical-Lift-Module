#ifndef ACTUATION_H
#define ACTUATION_H

#include <Arduino.h>
#include <ESP32Servo.h>
#include <Preferences.h>
#include <AccelStepper.h>
#include "WebSocketHandler.h"

#include "RFID.h"
#pragma once

extern const int HallSensor;
extern const int PUL;
extern const int DIR;

extern const String Loading_Bay;
extern const String Buffer_Bay;

extern MFRC522 mfrc522;
extern int current_floor;

extern Preferences preferences;

// Expose initialization and major functions
void initActuation(int leftDrawerPin, int rightDrawerPin);
void CalibrateLift();
String* DualCycle(const int iterations, String floors[], int OrdersPerFloor[], bool returnUIDs, int maxUIDs);
void ReorderShelves(const String move_from[], const String move_to[], const int num_iter);
void ProductRestock(const String Floor);
void ManualVerticalMotion(int steps, bool direction);
void ManualHorizontalMotion(int duration_ms, int left_pwm_freq, int right_pwm_freq);


#endif
