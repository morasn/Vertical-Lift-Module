#include "HardwareSerial.h"
#include "Actuation.h"
#include "OLED.h"

// Servo objects

Servo leftDrawer;
Servo rightDrawer;
AccelStepper stepper(1, PUL, DIR);
// Initialize Servos
void initActuation(int leftDrawerPin, int rightDrawerPin) {
  // Allow allocation of timers for multiple PWM channels
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  leftDrawer.setPeriodHertz(50);
  leftDrawer.attach(leftDrawerPin, 500, 2400);

  const int stop = preferences.getInt("Stop_Pulse", 1500);
  leftDrawer.writeMicroseconds(stop);

  rightDrawer.setPeriodHertz(50);
  rightDrawer.attach(rightDrawerPin, 500, 2400);
  rightDrawer.writeMicroseconds(stop);
  // stepper motor setup
  stepper.setAcceleration(1000);  // Standard acceleration
  // ESP32 Common Anode Inversion (Active LOW)
  stepper.setPinsInverted(false, false, false);  // DIR not inverted
}

// Consecutive-change (derivative) peak detector for 49E Hall sensor
// Detects ONE peak per magnet by finding where rate-of-change crosses zero
static int prev_reading = -1;
static int prev_prev_reading = -1;
static int baseline = -1;  // Store baseline for amplitude check
static bool peak_found_recently = false;
static unsigned long last_peak_millis = 0;
static int init_count = 0;
const int INIT_SAMPLES = 10;  // Ignore first N samples for stabilization

bool FloorPass(uint8_t HallSensor, bool calibration_mode) {
  int sensor = analogRead(HallSensor);
  
  // Initialize on first call
  if (prev_reading == -1) {
    prev_reading = sensor;
    prev_prev_reading = sensor;
    baseline = sensor;
    init_count = 0;
    displayMessage("Init: " + String(sensor));
    return false;
  }
  
  // Stabilization period - let readings settle and establish baseline
  if (init_count < INIT_SAMPLES) {
    // Average baseline during stabilization
    baseline = (baseline * init_count + sensor) / (init_count + 1);
    prev_prev_reading = prev_reading;
    prev_reading = sensor;
    init_count++;
    displayMessage("Stab " + String(init_count) + "/" + String(INIT_SAMPLES) + " B:" + String(baseline));
    return false;
  }
  
  // Calculate consecutive changes (derivatives)
  int change_now = sensor - prev_reading;           // Current rate of change
  int change_prev = prev_reading - prev_prev_reading; // Previous rate of change
  int amplitude = abs(sensor - baseline);            // Distance from baseline
  
  // Thresholds
  const int min_change = preferences.getInt("Min_Change", 30);        // Minimum derivative
  const int min_amplitude = preferences.getInt("Min_Amplitude", 200); // Minimum field strength
  const unsigned long refractory_ms = calibration_mode ? 100 : 200;   // Anti-double-count
  
  bool peak_detected = false;
  unsigned long now = millis();
  
  // PEAK DETECTION: Requires BOTH conditions:
  // 1. Derivative zero-crossing (was rising, now falling)
  // 2. Amplitude is significant (not just noise)
  if (!peak_found_recently) {
    // Was going UP (positive change_prev) and now going DOWN (negative change_now)
    bool derivative_crossed = (change_prev > min_change && change_now < -min_change);
    bool amplitude_significant = (amplitude > min_amplitude);
    
    if (derivative_crossed && amplitude_significant) {
      // Found peak! (derivative crossed zero AND field is strong)
      peak_detected = true;
      peak_found_recently = true;
      last_peak_millis = now;
      displayMessage("PEAK! S:" + String(sensor) + " A:" + String(amplitude));
    }
  }
  
  // Reset refractory period after timeout
  if (peak_found_recently && (now - last_peak_millis > refractory_ms)) {
    peak_found_recently = false;
  }
  
  // Debug display (throttled)
  static unsigned long last_debug = 0;
  if (now - last_debug > 100) {
    displayMessage("S:" + String(sensor) + " dS:" + String(change_now) + 
                   " A:" + String(amplitude));
    last_debug = now;
  }
  
  // Update history for next iteration
  prev_prev_reading = prev_reading;
  prev_reading = sensor;
  
  return peak_detected;
}



// Apply angle to servo motor
// push_shelf: true = pushing shelf into bay, false = pulling shelf from bay
void LiftControl(const int next_floor, const bool push_shelf) {
  int floors = next_floor - current_floor;
  if (floors == 0) return;  // already there

  int dir = (floors > 0) ? -1 : 1;
  int target_floors = abs(floors);

  const int normal_speed = preferences.getInt("Normal_Speed", 2720);        // 1600 * 1.7 steps per second (100 RPM)
  const int approach_speed = preferences.getInt("Approach_Speed", 1600);    // 1600 steps per second (26.7 RPM)
  const int steps_per_floor = preferences.getInt("Steps_Per_Floor", 1400);  // steps per floor (1.8 degree stepper with 1/16 microstepping and 1:2 pulley)

  int floors_passed = 0;
  bool last_floor_state = false;

  // Calculate base steps
  int base_steps = abs(floors) * steps_per_floor;
  
  // Calculate 5% overshoot/undershoot
  int adjustment = round(base_steps * 0.05);
  
  // Determine if we need overshoot or undershoot:
  // Going UP (floors > 0, dir = -1):
  //   - Pushing shelf: overshoot (go more up = more negative steps)
  //   - Pulling shelf: undershoot (go less up = less negative steps)
  // Going DOWN (floors < 0, dir = 1):
  //   - Pushing shelf: undershoot (go less down = less positive steps)
  //   - Pulling shelf: overshoot (go more down = more positive steps)
  
  int final_steps;
  if (floors > 0) {  // Going up
    if (push_shelf) {
      // Overshoot: go more up (more negative)
      final_steps = (base_steps + adjustment) * dir;
    } else {
      // Undershoot: go less up (less negative)
      final_steps = (base_steps - adjustment) * dir;
    }
  } else {  // Going down
    if (push_shelf) {
      // Undershoot: go less down (less positive)
      final_steps = (base_steps - adjustment) * dir;
    } else {
      // Overshoot: go more down (more positive)
      final_steps = (base_steps + adjustment) * dir;
    }
  }

  stepper.move(final_steps);  // set target position with overshoot/undershoot
  stepper.setMaxSpeed(normal_speed);

  unsigned long last_check = millis();
  displayMessage("Floors: " + String(floors) + " Adj: " + String(adjustment * (floors > 0 ? -1 : 1)) + " steps");
  while (stepper.run()) {

  }
  // stepper.stop();

  // Always update the global/current floor after motion completes
  current_floor = next_floor;
}

// Calibration function
void CalibrateLift() {
  const int speed = preferences.getInt("Approach_Speed", 1600);
  stepper.setMaxSpeed(speed);
  stepper.setSpeed(speed);  // Set constant speed

  // Move down a long distance (simulate infinite move)
  stepper.move(-150000);
  unsigned long last_check = millis();

  while (stepper.distanceToGo() != 0) {
    stepper.runSpeed(); // Run at constant speed, non-blocking

    // Check sensor periodically (non-blocking)
    if (millis() - last_check >= 10) {
      last_check = millis();
      if (FloorPass(HallSensor, true)) {
        stepper.stop();
        stepper.setCurrentPosition(0);  // Set current position as zero
        current_floor = 1;              // Assuming ground floor is 1
        displayMessage("Calibration complete");
        delay(2000);
        return;
      }
    }
    // Allow other tasks to run
    delayMicroseconds(100);
  }

  // If we got here, we reached the move limit without finding ground
  stepper.setCurrentPosition(0);
  current_floor = 1;
  displayMessage("Calib timeout");
}


// Motor Control of the Drawer

void DrawerControl(const bool Direction) {
  // Fixed timing: 8.5 seconds
  const int timeToWait = 9500; // milliseconds

  // Stop/neutral pulse (still read from preferences so your existing calibration works)
  const int stall_pulse = preferences.getInt("Stop_Pulse", 1500);

  // Requested PWM values (hard-coded as per your spec)
  const int PWM_FORWARD_Left = 800; // forward high-speed
  const int PWM_REVERSE_Left = 2200;  // reverse high-speed

  const int PWM_FORWARD_Right = 1870;
  const int PWM_REVERSE_Right = 1130;
  int pulse_left = 0;
  int pulse_right = 0;
  if (Direction == 1) {
    pulse_left = PWM_FORWARD_Left;
    pulse_right = PWM_FORWARD_Right;
  } else {
    pulse_left = PWM_REVERSE_Left;
    pulse_right = PWM_REVERSE_Right;
  }

 // Command motion for the full duration
  leftDrawer.writeMicroseconds(pulse_left);
  rightDrawer.writeMicroseconds(pulse_right);
  delay(timeToWait);

  // Hard stop to neutral
  leftDrawer.writeMicroseconds(stall_pulse);
  rightDrawer.writeMicroseconds(stall_pulse);
}

// Full cycle sequence
void ShelfRetrieve(const String next_floor_char, const String Bay_Stored_char) {
  const char side_next = next_floor_char.charAt(0);
  const char side_stored = Bay_Stored_char.charAt(0);

  const int next_floor = next_floor_char.substring(1).toInt();
  const int Bay_Stored = Bay_Stored_char.substring(1).toInt();

  // Move to next floor, then pull shelf from bay (false = pulling)
  LiftControl(next_floor, false);
  displayMessage("At floor " + String(current_floor) + "and should be at" + String(next_floor));
  delay(3000);
  if (side_next == 'F') {
    DrawerControl(0);  // push shelf to bay
  } else {
    DrawerControl(1);  // pull shelf from bay
  }

  // Move to Bay_Stored, then push shelf to bay (true = pushing)
  LiftControl(Bay_Stored, true);
  displayMessage("At floor " + String(current_floor) + "and should be at" + String(Bay_Stored));
  delay(3000);
  if (side_stored == 'F') {
    DrawerControl(1);  // pull shelf from bay
  } else {
    DrawerControl(0);  // push shelf to bay
  }
  
}

void ShelfReturn(const String target_floor_char) {
  const char side = target_floor_char.charAt(0);

  const int target_floor = target_floor_char.substring(1).toInt();

  DrawerControl(0);  // pull shelf from bay

  // Move to target floor, then push shelf to bay (true = pushing)
  LiftControl(target_floor, true);

  if (side == 'F') {
    DrawerControl(1);  // pull shelf from bay
  } else {
    DrawerControl(0);  // push shelf to bay
  }
}

String* DualCycle(const int iterations, String floors[], int OrdersPerFloor[], bool returnUIDs = false, int maxUIDs = 10) {
  static String collectedUIDs[10];  // Static array to store UIDs (adjust size as needed)
  int uidIndex = 0;                 // Index for storing UIDs

  displayMessage("Starting dispensing");

  // Simple case: only one shelf
  if (iterations == 1) {
    displayMessage("Loading shelf " + floors[0]);
    ShelfRetrieve(floors[0], Loading_Bay);
    displayMessage("Shelf Retrieved and is at Bay" + Loading_Bay);
    delay(2000);
    
    // LiftControl(Loading_Bay.substring(1).toInt());
    
    // Scan products
    int count = 0;
    String uid = "";
    while (count < OrdersPerFloor[0] && uidIndex < maxUIDs) {
      uid = getRFIDTextData();
      displayMessage("Waiting for Product " + String(count + 1) + "/" + String(OrdersPerFloor[0]));
      if (uid != "") {
        collectedUIDs[uidIndex++] = uid;
        count++;
        displayMessage("Scanned " + String(count) + "/" + String(OrdersPerFloor[0]));
      }
      delay(100);
    }
    
    // Return shelf
    displayMessage("Returning shelf " + floors[0]);
    ShelfReturn(floors[0]);
    displayMessage("Dispensing complete");
    return returnUIDs ? collectedUIDs : nullptr;
  }
  else{
      // Multi-shelf case: use dual-bay buffering
  // Pre-load first two shelves
  displayMessage("Loading shelf " + floors[0]);
  ShelfRetrieve(floors[0], Loading_Bay);
  displayMessage("Pre-loading shelf " + floors[1]);
  ShelfRetrieve(floors[1], Buffer_Bay);

  for (int i = 0; i < iterations; i++) {
    displayMessage("Dispensing from " + floors[i]);
    
    // Move to loading bay for scanning (neutral move, use false as default)
    LiftControl(Loading_Bay.substring(1).toInt(), false);

    // Scan products from current shelf (in Loading_Bay)
    int count = 0;
    String uid = "";
    while (count < OrdersPerFloor[i] && uidIndex < maxUIDs) {
      uid = getRFIDTextData();
      displayMessage("Waiting for Product " + String(count + 1) + "/" + String(OrdersPerFloor[i]));
      if (uid != "") {
        collectedUIDs[uidIndex++] = uid;
        count++;
        displayMessage("Scanned " + String(count) + "/" + String(OrdersPerFloor[i]));
      }
      delay(100);
    }

    // Return current shelf to its position
    displayMessage("Returning shelf " + floors[i]);
    ShelfReturn(floors[i]);

    // If not last iteration, prepare next shelf
    if (i < iterations - 1) {
      // Move buffered shelf to loading bay
      displayMessage("Moving buffer to loading");
      ShelfRetrieve(Buffer_Bay, Loading_Bay);
      
      // Pre-fetch next shelf to buffer (if available)
      if (i + 2 < iterations) {
        displayMessage("Pre-loading shelf " + floors[i + 2]);
        ShelfRetrieve(floors[i + 2], Buffer_Bay);
      }
    }
  }
  }



  displayMessage("Dispensing complete");

  // Return the collected UIDs if requested, otherwise nullptr
  return returnUIDs ? collectedUIDs : nullptr;
}

// Shelf reordering function
void ReorderShelves(const String move_from[], const String move_to[], const int num_iter) {
  displayMessage("Reordering shelves");
  // Implementation of shelf reordering logic
  for (int i = 0; i < num_iter; i++) {
    String from = move_from[i];
    String to = move_to[i];


    // Add your reordering logic here
    // Move to source, pull shelf
    LiftControl(from.substring(1).toInt(), false);

    if (from.charAt(0) == 'F') {
      DrawerControl(0);  // pull shelf from bay
    } else {
      DrawerControl(1);  // push shelf to bay
    }

    // Move to destination, push shelf
    LiftControl(to.substring(1).toInt(), true);
    if (to.charAt(0) == 'F') {
      DrawerControl(1);  // pull shelf from bay
    } else {
      DrawerControl(0);  // push shelf to bay
    }

    // Return to a safe position (neutral move)
    LiftControl(Loading_Bay.substring(1).toInt(), false);
  }
  displayMessage("Reordering complete");
}

void ProductRestock(const String Floor) {
  displayMessage("Restocking on " + Floor);
  ShelfRetrieve(Floor, Loading_Bay);
  ShelfReturn(Floor);
  displayMessage("Restock complete");
}


void ManualVerticalMotion(int steps, bool direction) {
  int speed = preferences.getInt("Approach_Speed", 1600);
  stepper.setMaxSpeed(speed);

  // direction: true = forward, false = backward
  int move_steps = direction ? -steps : steps;
  stepper.move(move_steps);
  while (stepper.run()) {
    // stepper.run();
  }
}

void ManualHorizontalMotion(int duration_ms, int left_pwm_freq, int right_pwm_freq) {
  // Set drawer motion
  leftDrawer.writeMicroseconds(left_pwm_freq);
  rightDrawer.writeMicroseconds(right_pwm_freq);

  delay(duration_ms);

  const int stop = preferences.getInt("Stop_Pulse", 1500);
  leftDrawer.writeMicroseconds(stop);   // stop
  rightDrawer.writeMicroseconds(stop);  // stop
}