#include "Actuation.h"
#include "RFID.h"
#include "WebSocketHandler.h"
#include "Numpad.h"


const int HallSensor = 3;

const String Loading_Bay = "F5"; // ground floor
const String Buffer_Bay = "F3"; // Bay for Buffer

// Arduino RFID pin definitions for RC522
#define RST_PIN 4 
#define SS_PIN 9 // Slave Select pin also known as SDA pin
MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance


int current_floor = 0;


void setup() {
  const int LiftMotorPin = 12; // Pin connected to the lift motor
  const int DrawerMotorPin = 11; // Pin connected to the lift motor

  const int BuzzerPin = 2; // Pin connected to the buzzer
  const int CalibrationButtonPin = 3; // Pin connected to the calibration button


  initActuation(LiftMotorPin, DrawerMotorPin);
  pinMode(BuzzerPin, OUTPUT);
  pinMode(CalibrationButtonPin, INPUT_PULLUP);
  pinMode(HallSensor, INPUT);
  Serial.begin(11300); // Initialize serial communications with the PC
  
  // RFID Initialization
  SPI.begin();        // Init SPI bus
  mfrc522.PCD_Init(); // Init MFRC522

	// Initialize WiFi
	initWiFi("MySSID", "MyPassword");

	// Initialize WebSocket (point to your Flask WS endpoint)
	initWebSocket("ws://192.168.1.100:8765/ws");

  CalibrateLift(CalibrationButtonPin);
}

void loop() {
	handleWebSocket(); // check for any websocket
  KeyPadInterpret();
  delay(100);
  // Look for new RFID cards
}
