#ifndef WEBSOCKETHANDLER_H
#define WEBSOCKETHANDLER_H

#include <WebSocketsClient.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include "Actuation.h"
#include "OLED.h"

extern bool Authenticated;
extern int8_t AuthTrials;
extern int VLMtransactionID;
extern bool AutoRestocked;
extern Preferences preferences;
extern const int HallSensor;

void initWiFi(const char *ssid, const char *password);
void initWebSocket(const char *serverUrl, const int port);
void handleWebSocket();
void sendMessage(JsonDocument msg_json);

#endif
