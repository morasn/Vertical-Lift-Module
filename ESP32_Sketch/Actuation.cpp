#include "Actuation.h"

// Servo objects
Servo Lift;
Servo Drawer;


// Initialize Servos
void initActuation(int liftPin, int drawerPin) {
    Lift.attach(liftPin);
    Drawer.attach(drawerPin);
}

// Magnetic Reader counter
bool FloorPass(uint8_t HallSensor){
  const int Min = 25;
  int sensor = analogRead(HallSensor);
  
  if (sensor > Min) {
    return true; 
  }
  else {
    return false;
  }
}

// // Compute rotation angle (mm → degrees)
float AngleRotation(const int Diameter,const int Distance) {
    // circumference = π*D → steps per mm
    float degreesPerMM = 360.0 / (PI * Diameter);
    return Distance * degreesPerMM;
}


// Apply angle to servo motor
void LiftControl(const int next_floor) {

    const int floors = next_floor - current_floor;
    const int normal_delay = 5;
    const int approaching_delay = 10;
    const int step = 1;
    
    int currentAngle = Lift.read();
    int floors_passed = 0;
      
      
    while (floors_passed < floors) {
      
      if (floors>0){
        currentAngle = currentAngle + step;
      }
      else {
        currentAngle = currentAngle - step;
      }
      Lift.write(currentAngle);
      
      bool floor_passed = FloorPass(HallSensor);
      
      if (floor_passed){
        floors_passed++;
      }
      if (floors_passed < (floors - 1)){
        delay(normal_delay);
      }
      else {
        delay(approaching_delay);
      }
    }

}


// Calibration function
void CalibrateLift(const int SensorPin) {
  const int delay_val = 5;
  const int step = 1;
  int currentAngle = Lift.read();
    while (digitalRead(SensorPin) == LOW) {
        currentAngle = currentAngle - step;
        Lift.write(currentAngle);
        delay(delay_val);
    }

}


// Motor Control of the Drawer
void DrawerControl(const bool Direction) {
    const int Diameter = 48; // in mm
    const int Distance = 100; // in mm
    float Angle = AngleRotation(Diameter, Distance);
    if (!Direction) Angle = -Angle; // reverse direction
    int target = constrain((int)Angle, 0, 180);
    Drawer.write(target);

}

// Full cycle sequence
void ShelfRetrieve(const String next_floor_char, const String Bay_Stored_char) {
    const char side = next_floor_char.charAt(0);
    
    const int next_floor = next_floor_char.substring(1).toInt();
    const int Bay_Stored = Bay_Stored_char.substring(1).toInt();

    LiftControl(next_floor);
    
    if (side == 'F') {
        DrawerControl(1); // push shelf to bay
    } else {
        DrawerControl(0); // pull shelf from bay
    }
    
    LiftControl(Bay_Stored);
    if (side == 'B') {
        DrawerControl(0); // pull shelf from bay
    } else {
        DrawerControl(1); // push shelf to bay
    }
}

void ShelfReturn(const String target_floor_char) {
    const char side = target_floor_char.charAt(0);
    
    const int target_floor = target_floor_char.substring(1).toInt();

    if (side == 'F') {
        DrawerControl(1); // push shelf to bay
    } else {
        DrawerControl(0); // pull shelf from bay
    }
    
    LiftControl(target_floor);

    if (side == 'B') {
        DrawerControl(0); // pull shelf from bay
    } else {
        DrawerControl(1); // push shelf to bay
    }
}

String* DualCycle(const int iterations, String floors[], int OrdersPerFloor[], bool returnUIDs = false, int maxUIDs = 10) {
  static String collectedUIDs[10];  // Static array to store UIDs (adjust size as needed)
  int uidIndex = 0;  // Index for storing UIDs

  for (int i = 0; i < iterations; i++) {
    ShelfRetrieve(floors[i], Loading_Bay); 
    ShelfRetrieve(floors[i + 1], Buffer_Bay);
    LiftControl(Loading_Bay.substring(1).toInt());
    
    // Always check for UIDs
    int count = 0;
    String uid = "";
    while (count < OrdersPerFloor[i] && uidIndex < maxUIDs) {
      uid = RFID_SCAN_CHECK();
      if (uid != "") {  // Increment only on valid UID
        collectedUIDs[uidIndex++] = uid;  // Store the UID
        count++;
      } 
      delay(100);  // Small delay to avoid CPU hogging
    }

    ShelfReturn(floors[i]);
    ShelfRetrieve(Buffer_Bay, Loading_Bay);
    ShelfReturn(floors[i + 1]);
  }

  // Return the collected UIDs if requested, otherwise nullptr
  return returnUIDs ? collectedUIDs : nullptr;
}

// Shelf reordering function
void ReorderShelves(const String move_from[], const String move_to[], const int num_iter) {
    // Implementation of shelf reordering logic
    for (int i = 0; i < num_iter; i++) {
        String from = move_from[i];
        String to = move_to[i];
        
        
        // Add your reordering logic here
        // Example: LiftControl(from); DrawerControl(0); LiftControl(to); DrawerControl(1);
        LiftControl(from.substring(1).toInt());
        
        if (from.charAt(0) == 'F') {
            DrawerControl(0); // pull shelf from bay
        } else {
            DrawerControl(1); // push shelf to bay
        }

        LiftControl(to.substring(1).toInt());
        if (to.charAt(0) == 'B') {
            DrawerControl(0); // pull shelf from bay
        } else {
            DrawerControl(1); // push shelf to bay
        }

        LiftControl(Loading_Bay.substring(1).toInt()); // Return to a safe position
    }
}

void ProductRestock(const String Floor){
  ShelfRetrieve(Floor, Loading_Bay);
  ShelfReturn(Floor);
}