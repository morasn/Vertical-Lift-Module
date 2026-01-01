#ifndef OLED_H
#define OLED_H

#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64  // OLED display height, in pixels

extern Adafruit_SSD1306 display;

// Initialize the global `display` instance. Call `initOLED()` from setup().
void initOLED();

void displayMessage(const String &message);
void HomeMessage();

#endif
