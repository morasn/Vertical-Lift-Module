# Smart Vertical Lift Module (VLM) Prototype

> **Automated Storage and Retrieval System (AS/RS) with RFID Integration and Dual-Cycle Operation**

## 📖 Project Overview
This project involves the development of a scaled **Vertical Lift Module (VLM)** prototype designed to optimize warehouse storage efficiency. The system automates the storage and retrieval of items using a vertically moving lift mechanism, maximizing vertical space utilization. 

Unlike traditional storage systems, this prototype integrates **RFID technology** for real-time, error-free tracking of unpackaged items and implements a **dual-cycle operation** strategy. This allows the system to store one item and retrieve another in a single motion cycle, significantly reducing idle time and increasing throughput.

## ✨ Key Features
* **Automated Vertical Storage:** Maximizes storage density by utilizing vertical space with dynamic shelf allocation
* **RFID Integration:** Uses RC522 RFID readers for real-time identification and tracking of tools/items without manual scanning
* **Dual-Cycle Operation:** Simultaneous storage and retrieval capabilities to minimize machine downtime
* **Smart Inventory Management:** Features project-based data clustering and inventory forecasting to streamline shelf ordering
* **Web-Based Interface:** A user-friendly Flask web dashboard for operators to request items, manage inventory, and view logs
* **Real-Time Communication:** WebSocket-based bidirectional communication between ESP32 and server for instant updates
* **Comprehensive Logging:** Transaction logging with detailed event tracking for audit trails and debugging
* **Manual Control Interface:** Direct motor control capabilities via web interface for maintenance and calibration

## 🏗️ System Architecture

### **Backend Architecture**
The system follows a modular Python architecture:
* **Flask Web Server** (`app.py`): Main web application with RESTful API endpoints
* **Backend Logic** (`Backend.py`): Business logic for product operations and image processing
* **VLM Control** (`VLM_Control.py`): Interfaces with ESP32 for dispensing and restocking operations
* **WebSocket Server** (`Websocket_Server.py`): Asynchronous WebSocket server running on port 8765
* **Database Layer** (`DB/DB_Back.py`): SQLite connection pooling and database operations
* **Forecasting Module** (`Forecast.py`): Inventory prediction and optimization algorithms

### **Communication Flow**
```
Web Interface (Flask:5000) ←→ Backend Logic ←→ Database (SQLite)
                                      ↓
                            WebSocket Server (8765)
                                      ↓
                            ESP32 (WebSocket Client)
                                      ↓
                          Motors, Sensors, RFID
```

## 🛠️ Hardware Architecture

### **Electronics & Control**
* **Microcontroller:** ESP32 DevKit (dual-core, WiFi enabled)
* **RFID Module:** RC522 (SPI communication) for item scanning
* **Actuators:**
    * Stepper Motor (Vertical motion with DIR/STEP control)
    * DC Servo Motors (Horizontal drawer extension - left and right)
* **Sensors:** 
    * Hall Effect Sensor (Floor positioning and homing)
* **Display:** OLED SSD1306 128x64 (I2C) for status messages and system information
* **IO Expansion:** PCF8574 I2C expander (for keypad interface)
* **Input Device:** I2C Keypad (for operator identification)
* **Audio:** Buzzer (user feedback)

### **Mechanical Design**
* **Drive System:** Chain drive system for high load capacity and durability
* **Structure:** Wooden frame prototype (scaled model) with steel shafts and customized 3D printed/manufactured holders
* **Loading Bay:** Floor F2 (ground floor for operator interaction)
* **Buffer Bay:** Floor F1 (intermediate storage for dual-cycle operations)

## 🔌 ESP32 Pin Configuration
| GPIO | Component / Function | Protocol |
| :--- | :--- | :--- |
| 34 | Hall Effect Sensor (Analog Input) | ADC1 |
| 14 | Stepper Motor DIR | Digital Out |
| 15 | Stepper Motor STEP/PUL | Digital Out |
| 16 | OLED SDA | I2C (Wire) |
| 17 | OLED SCL | I2C (Wire) |
| 5 | RC522 RFID SS/SDA | SPI |
| 18 | RC522 SCK | SPI |
| 19 | RC522 MISO | SPI |
| 21 | RC522 RST | Digital Out |
| 23 | RC522 MOSI | SPI |
| 32 | Right Drawer Servo Motor | PWM |
| 33 | Left Drawer Servo Motor | PWM |
| 25 | PCF8574 Extender SDA | I2C (TwoWire) |
| 26 | PCF8574 Extender SCL | I2C (TwoWire) |
| 27 | Buzzer | Digital Out |

## 📁 Folder Structure
```
Control/
├── app.py                          # Main Flask application
├── Backend.py                      # Business logic and product operations
├── VLM_Control.py                  # ESP32 control interface
├── Websocket_Server.py             # WebSocket server for ESP32 communication
├── Forecast.py                     # Inventory forecasting algorithms
├── shared_states.py                # Shared application state variables
├── requirements.txt                # Python dependencies
├── tester.py                       # Testing utilities
├── README.md                       # Project documentation
│
├── DB/                             # Database layer
│   ├── DB_Back.py                  # Database operations with connection pooling
│   ├── DB_Create.py                # Database schema creation
│   └── DB.db                       # SQLite database file
│
├── ESP32_Sketch/                   # ESP32 firmware (Arduino C++)
│   ├── ESP32_Sketch.ino            # Main Arduino sketch
│   ├── WebSocketHandler.cpp/.h     # WebSocket client implementation
│   ├── Actuation.cpp/.h            # Motor control functions
│   ├── RFID.cpp/.h                 # RFID reader interface
│   ├── OLED.cpp/.h                 # Display functions
│   └── Numpad.cpp/.h               # Keypad input handling
│
├── static/                         # Static web assets
│   └── DB/
│       ├── Product_Pics/           # Product images organized by ID
│       └── Compress_Temp/          # Temporary image processing
│
├── templates/                      # Flask HTML templates
│   ├── layout.html                 # Base template
│   ├── index.html                  # Main dashboard
│   ├── login.html                  # Login page
│   ├── product.html                # Product details
│   ├── project.html                # Project-based dispensing
│   ├── view_inventory.html         # Inventory management
│   ├── config_VLM.html             # VLM configuration interface
│   ├── machine_logs.html           # System logs viewer
│   ├── add_product.html            # Product creation form
│   └── add_shelf.html              # Shelf management
│
├── Documentation/                  # System documentation
│   ├── WebSocket_Messages_Documentation.md
│   ├── Charts/                     # System flowcharts
│   ├── ESP32/                      # ESP32 state diagrams 
│   └── Website_Functions/          # Web function flowcharts
│
├── Optimization/                   # ML and optimization modules
│   ├── Optimization.py             # Optimization algorithms
```

## 📋 Prerequisites

### **Hardware Requirements**
* ESP32 Development Board (DevKit or compatible)
* RC522 RFID Module
* Stepper Motor with Driver (e.g., A4988, DRV8825)
* 2x Servo Motors
* Hall Effect Sensor (Analog)
* SSD1306 OLED Display (128x64, I2C)
* PCF8574 I2C IO Expander
* I2C Keypad (3x4 or 4x4)
* Buzzer
* Appropriate power supplies

### **Software Requirements**
* **Python 3.8+** (for server)
* **Arduino IDE 1.8+** or **PlatformIO** (for ESP32 firmware)
* **SQLite3** (usually included with Python)
* Modern web browser (Chrome, Firefox, Edge)

### **ESP32 Libraries** (install via Arduino Library Manager)
* `WebSocketsClient` by Markus Sattler
* `ArduinoJson` by Benoit Blanchon (v6.x)
* `MFRC522` by GithubCommunity
* `Adafruit SSD1306`
* `Adafruit GFX Library`
* `PCF8574` by Renzo Mischianti
* `I2CKeyPad` by Rob Tillaart
* `Preferences` (ESP32 built-in)

### **Python Packages**
* Flask
* Pillow (PIL)
* bcrypt
* websockets

## 🚀 Installation Steps

### **1. Clone the Repository**
```bash
git clone <repository-url>
cd Control
```

### **2. Set Up Python Environment**
```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **3. Initialize Database**
```bash
# Run database creation script
python DB/DB_Create.py
```

### **4. Configure ESP32 Firmware**
1. Open `ESP32_Sketch/ESP32_Sketch.ino` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   initWiFi("YOUR_SSID", "YOUR_PASSWORD");
   ```
3. Update WebSocket server IP address:
   ```cpp
   initWebSocket("SERVER_IP_ADDRESS", 8765);
   ```
4. Install required libraries (see Prerequisites)
5. Select board: **ESP32 Dev Module** from Tools → Board
6. Upload sketch to ESP32

### **5. Configure Application Settings**
Edit `shared_states.py` to configure shelf properties and system parameters:
```python
shelf_properties = {
    'min_level': 1,
    'max_level': 10,  # Adjust based on your VLM height
}
```

### **6. Start the Application**
```bash
# Run the Flask application (WebSocket server starts automatically)
python app.py
```

The application will be accessible at:
* **Web Interface:** `http://localhost:5000`
* **WebSocket Server:** `ws://localhost:8765`

### **7. First Time Setup**
1. Navigate to `http://localhost:5000` in your browser
2. Create the first operator account (Super Admin)
3. Log in with the created credentials
4. Add shelves via the web interface
5. Add products to the inventory

### **8. Network Configuration**
For production deployment:
* Update Flask host in `app.py`: `app.run(host='0.0.0.0', port=5000)`
* Configure firewall to allow ports 5000 (Flask) and 8765 (WebSocket)
* Update ESP32 firmware with server's network IP address

## 💻 Software & Communication

### **WebSocket Message Protocol**
The system uses JSON-formatted messages over WebSocket for ESP32 communication:

**Authentication (Code 120):**
```json
{"code": 120, "operator": "operator_id"}
```

**Dispense Operation (Code 200):**
```json
{
  "code": 200,
  "transaction_id": 12345,
  "floors": ["F5", "F3"],
  "products": [["PROD1"], ["PROD2", "PROD3"]],
  "orders_per_floor": [1, 2]
}
```

**Configuration Update (Code 501):**
```json
{
  "code": 501,
  "Normal_Speed": 1000,
  "Approach_Speed": 500,
  "Steps_Per_Floor": 2000,
  ...
}
```

**Manual Control:**
* **Vertical Motor (Code 600):** Step control
* **Horizontal Motor (Code 601):** PWM control with duration
* **Hall Sensor Read (Code 602):** Immediate sensor reading

See `Documentation/WebSocket_Messages_Documentation.md` for complete protocol specification.

### **Database Schema**
The SQLite database includes the following main tables:
* **OPERATORS:** User authentication and access levels
* **PRODUCTS:** Product catalog with specifications
* **SHELVES:** Shelf locations and properties
* **PRODUCTS_SHELVES:** Product-shelf relationships with quantities
* **TRANSACTIONS:** Dispense/restock transaction history
* **LOGS:** System events and debugging information
* **PROJECTS:** Project-based product groupings
* **VLM_CONFIGURATION:** Machine parameters

## 🔧 Configuration & Calibration

### **VLM Configuration Parameters**
Access via web interface at `/config_vlm`:
* **Normal_Speed:** Motor speed for normal operation (steps/sec)
* **Approach_Speed:** Slower speed when approaching target floor
* **Steps_Per_Floor:** Stepper steps between floors (requires calibration)
* **Stop_Pulse, For_Pulse, Back_Pulse:** Horizontal motor PWM frequencies
* **Collect_Time, Return_Time:** Drawer extension/retraction durations (ms)
* **hall_N_thresh, hall_S_thresh:** Hall sensor thresholds for floor detection

### **Calibration Procedure**
1. Use manual vertical control to move one complete floor
2. Count steps or measure encoder feedback
3. Update `Steps_Per_Floor` in configuration
4. Test and adjust hall sensor thresholds for reliable detection
5. Calibrate horizontal motor timings for complete drawer extension

## 📊 API Endpoints

### **Authentication**
* `GET /login` - Login page
* `POST /login` - Authenticate user
* `GET /logout` - End session
* `GET /create_first_operator` - Initial setup

### **Product Management**
* `GET /` - Main dashboard with products
* `GET /product/<product_id>` - Product details
* `GET /add_product` - Product creation form
* `POST /add_product` - Create new product
* `GET /api/product_inventory/<product_id>` - Get inventory data

### **Operations**
* `GET /api/product_interaction/<product_id>/<operation>` - Dispense/restock
* `GET /api/project_dispense/<project_id>` - Multi-product project dispensing
* `GET /project/<project>` - Project page

### **System Management**
* `GET /config_vlm` - VLM configuration interface
* `GET/POST /api/vlm_config` - Get/update VLM parameters
* `POST /api/vlm_vertical` - Manual vertical control
* `POST /api/vlm_horizontal` - Manual horizontal control
* `GET /api/vlm_hall_immediate` - Read hall sensor
* `GET /machine_logs` - System logs viewer
* `GET /api/logs` - Fetch filtered logs
* `GET /debug/ws_status` - WebSocket connection status

## 🧪 Testing & Debugging

### **Log Levels**
* **INFO:** Normal operations and state changes
* **WARNING:** Non-critical issues and failed authentication attempts
* **ERROR:** Critical errors requiring attention

### **Debugging Tools**
* **Machine Logs Page:** Web-based log viewer with filtering
* **WebSocket Status:** Check connection health at `/debug/ws_status`
* **Serial Monitor:** ESP32 debug output via USB
* **Transaction Tracking:** All operations logged with unique transaction IDs



## 🤝 Contributing
This is an academic project. For questions or suggestions, please contact the project team.

## 📞 Support
For technical support or inquiries, please refer to the project documentation or contact the development team.