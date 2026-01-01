#include "Actuation.h"
#include "RFID.h"
#include "WebSocketHandler.h"
#include "Numpad.h"
#include "OLED.h"

#include <Wire.h>
#include <Preferences.h>


const int HallSensor = 34; // Pin connected to the hall effect sensor (ADC1 pin, compatible with WiFi)

const int PUL = 15;
const int DIR = 14;

const int LeftDrawerMotorPin = 33; // Pin connected to the left drawer motor
const int RightDrawerMotorPin = 32; // Pin connected to the right drawer motor

const int BuzzerPin = 27; // Pin connected to the buzzer

const int OLED_SDA = 16;
const int OLED_SCL = 17;

const String Loading_Bay = "F2"; // ground floor
const String Buffer_Bay = "F1"; // Bay for Buffer

const int Extend_SDA = 25;
const int Extend_SCL = 26;
TwoWire I2CExtender = TwoWire(1);
PCF8574 pcf8574( &I2CExtender, 0x20); // Use the new bus for the extender

extern I2CKeyPad  keypad;

// Arduino RFID pin definitions for RC522
#define RST_PIN 21
#define SS_PIN 5 // Slave Select pin also known as SDA pin
const int8_t SCK_Pin = 18;
const int8_t MOSI_Pin = 23;
const int8_t MISO_Pin = 19;


MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

// OLED display instance
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

int current_floor = 1;

Preferences preferences;


void setup() {
  Serial.begin(115200); // Initialize serial communications with the PC
  Serial.println("Motor Pin Init...");
  initActuation(LeftDrawerMotorPin, RightDrawerMotorPin);

  Serial.print("Init OLED I2C...");
  Wire.begin(OLED_SDA, OLED_SCL);
  initOLED();

  displayMessage("System Initializing...");


  displayMessage("Motors ready");

  // Initialize WiFi
  delay(100);
	displayMessage("Wifi Connecting");
  Serial.println("Initializing WiFi...");
	initWiFi("VLM-Thesis", "3ayezAPass");
	// Initialize WebSocket (point to your Flask WS endpoint)
	Serial.println("Initializing WebSocket...");
	initWebSocket("192.168.137.1", 8765);
	handleWebSocket();
  delay(2000);
  handleWebSocket();
  
  Serial.println("RFID Starting...");
  displayMessage("RFID Initializing");
  // Explicitly initialize SPI with correct pins
  SPI.begin(SCK_Pin, MISO_Pin, MOSI_Pin, SS_PIN);
  delay(250); // Longer delay
  mfrc522.PCD_Init();
  delay(150); // Longer delay
  mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);
  delay(50);
  // Verify communication
  mfrc522.PCD_DumpVersionToSerial();
  Serial.println("RFID Ready!");
  displayMessage("RFID ready");


  Serial.println("Init Extender...");
  I2CExtender.begin(Extend_SDA, Extend_SCL);
  
  displayMessage("Extender ready");
  // Initialize keypad (defined in Numpad.cpp)
  KeypadInit();
  displayMessage("Numpad ready");


  Serial.println("Pin Mode Init...");
  pinMode(BuzzerPin, OUTPUT);

  pinMode(HallSensor, INPUT);
  pinMode(PUL, OUTPUT);
  pinMode(DIR, OUTPUT);
  displayMessage("Pins ready");
  delay(100);

  preferences.begin("operation", false);
  // delay(2000);
  Serial.println("Lift Calibrating");
  displayMessage("Lift Calibrating! Kindly wait :)");
  // CalibrateLift();
  Serial.println("System is Ready!");
  displayMessage("System is Ready!");
  delay(1000);
  HomeMessage();
}

void loop() {
	handleWebSocket(); // check for any websocket
  KeyPadInterpret(keypad);
  // RFID_Send();
  delay(100);
  // Look for new RFID cards
}
