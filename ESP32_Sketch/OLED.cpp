
#include "OLED.h"
// #include <Wire.h>

// Define the global display instance used across the sketch.
// Constructor: width, height, TwoWire*, reset_pin (-1 if unused)
// Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void initOLED() {
  // Initialize the OLED display
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for (;;); // Don't proceed, loop forever
  }
  display.clearDisplay();
  
  display.drawPixel(10, 10, WHITE);
  display.display();
}

void clearOLED() {
  display.clearDisplay();
  // display.display();
}

void displayMessage(const String &message) {
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(WHITE);
  display.setCursor(1, 1);
  // display.println("Hello, world!");
  display.println(message);
  display.display(); 
}

void HomeMessage() {
  displayMessage("Press A to proceed\nor B for auto restock");
}