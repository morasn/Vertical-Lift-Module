#ifndef WEBSOCKETHANDLER_H
#define WEBSOCKETHANDLER_H

#include <WebSocketsClient.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include "Actuation.h"

extern bool Authenticated;
extern int AuthTrials;
extern int VLMtranscationID;

void initWiFi(const char *ssid, const char *password);
void initWebSocket(const char *serverUrl);
void handleWebSocket();
void sendMessage(JsonDocument msg_json);

#endif
