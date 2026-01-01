import sqlite3 

db = sqlite3.connect('DB/DB.db')
cursor = db.cursor()

# cursor.execute('DROP TABLE SHELVES;')
# cursor.execute('DROP TABLE PRODUCTS;')
# cursor.execute('DROP TABLE OPERATORS;')
# cursor.execute('DROP TABLE PRODUCTS_SHELVES;')
# cursor.execute('DROP TABLE TRANSACTIONS;')
# cursor.execute('DROP TABLE PRODUCT_TAGS;')
# cursor.execute('DROP TABLE PRODUCT_PROJECTS;')
cursor.execute('DROP TABLE LOGS;')
# cursor.execute('DROP TABLE FORECASTS;')
cursor.execute('DROP TABLE VLM_CONFIG;')


# # Pos (L/R row-> upto 999 rows)
# cursor.execute('''CREATE TABLE IF NOT EXISTS SHELVES (
#                ID TEXT PRIMARY KEY,
#                Pos CHARACTER(3) NOT NULL,
#                Weight FLOAT(2),
#                Quantity INT DEFAULT 0,
# 			   SpaceLeft INT DEFAULT 100,
# 			   RacksAvailable INT DEFAULT 1,
#                UNIQUE (Pos, ID)
# );
# ''')

# cursor.execute('''CREATE TABLE IF NOT EXISTS PRODUCTS (
#                ID TEXT PRIMARY KEY,
#                Name TEXT NOT NULL,
#                Description TEXT,
#                Family_Name TEXT,
#                Family_Item TEXT,
#                Weight FLOAT(2),
#                ROP INT DEFAULT 0,
#                OH INT DEFAULT 0,
# 			   Length FLOAT(2),
# 			   Width FLOAT(2),
#                Height FLOAT(2),
#                UNIQUE (ID)
# );
# ''')

# cursor.execute('''CREATE TABLE IF NOT EXISTS OPERATORS (
#                ID INT,
#                NAME TEXT NOT NULL,
#                Username TEXT,
#                Password TEXT NOT NULL,
#                Password_Salt TEXT NOT NULL,
#                Access_Level INT DEFAULT 1,
#                PRIMARY KEY (ID, Username)
# );
# ''')
# Access Levels:
# 1: Operator (Can add/remove stock, view products)
# 2: Manager (Can add/remove products)
# 3: Admin (can add/remove operators)
# 4: Super Admin (can manage all aspects)

# cursor.execute('''CREATE TABLE IF NOT EXISTS PRODUCTS_SHELVES (
#                Shelf_ID INT,
#                Product_ID TEXT,
#                Quantity INT,
#                PRIMARY KEY (Shelf_ID, Product_ID),
#                FOREIGN KEY (Shelf_ID) REFERENCES SHELVES(ID) ON DELETE CASCADE,
#                FOREIGN KEY (Product_ID) REFERENCES PRODUCTS(ID) ON DELETE CASCADE
# );
# ''')

# cursor.execute('''CREATE TABLE IF NOT EXISTS TRANSACTIONS (
#                ID INT,
#                Product_ID TEXT,
#                Project_Name TEXT,
#                Shelf_ID TEXT,
#                Time TEXDATETIME DEFAULT CURRENT_TIMESTAMPT,
#                Quantity_Added INT,
#                Quantity_Removed INT,
#                Operator_ID INT,
#                PRIMARY KEY (ID, Product_ID, Shelf_ID),
#                FOREIGN KEY (Shelf_ID) REFERENCES SHELVES(ID) ON DELETE CASCADE,
#                FOREIGN KEY (Product_ID) REFERENCES PRODUCTS(ID) ON DELETE CASCADE
#                FOREIGN KEY (Operator_ID) REFERENCES OPERATORS(ID) ON DELETE CASCADE
#                FOREIGN KEY (Project_Name) REFERENCES PRODUCT_PROJECTS(Project) ON DELETE CASCADE
# );
# ''')

# cursor.execute('''CREATE TABLE IF NOT EXISTS PRODUCT_TAGS (
#                Product_ID TEXT,
#                Tag TEXT,
#                PRIMARY KEY (Product_ID,Tag),
#                FOREIGN KEY (Product_ID) REFERENCES PRODUCTS(ID) ON DELETE CASCADE
# );
# ''')

# cursor.execute('''CREATE TABLE IF NOT EXISTS PRODUCT_PROJECTS (
#                Product_ID TEXT,
#                Project TEXT,
#                PRIMARY KEY (Product_ID, Project),
#                FOREIGN KEY (Product_ID) REFERENCES PRODUCTS(ID) ON DELETE CASCADE
# );
# ''')

cursor.execute('''CREATE TABLE IF NOT EXISTS LOGS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            Transaction_Type TEXT NOT NULL,  -- e.g., 'ADD', 'REMOVE', 'UPDATE'
			Transaction_ID TEXT,  
			Level TEXT NOT NULL,  -- e.g., 'INFO', 'ERROR', 'WARNING'
            Source TEXT,
			Message TEXT NOT NULL
			
);
''')


# cursor.execute('''CREATE TABLE IF NOT EXISTS FORECASTS (
#     ID INTEGER PRIMARY KEY AUTOINCREMENT,
#     Product_ID TEXT,            -- nullable
#     Project_Name TEXT,          -- nullable
#     Forecasted_On DATETIME,
#     Target_Date DATETIME,
#     Forecast_Quantity INT,
#     Model_Name TEXT,
#     Created_By TEXT,
#     Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
#     FOREIGN KEY (Product_ID) REFERENCES PRODUCTS(ID) ON DELETE CASCADE,
#     FOREIGN KEY (Project_Name) REFERENCES PRODUCT_PROJECTS(Project) ON DELETE CASCADE
# );''')

# cursor.execute('''ALTER TABLE OPERATOR RENAME TO OPERATORS''')
# cursor.execute('''ALTER TABLE SHELVES ADD COLUMN Height FLOAT(1)''')
# cursor.execute('''ALTER TABLE PRODUCTS_SHELVES RENAME COLUMN Shelf to Shelf_ID''')


cursor.execute('''CREATE TABLE IF NOT EXISTS VLM_CONFIG (
	Normal_Speed INT ,
	Approach_Speed INT,
	Steps_Per_Floor INT ,
	Stop_Pulse INT ,
	For_Pulse INT ,
	Back_Pulse INT ,
	Collect_Time INT ,
	Return_Time INT,
	hall_N_thresh INT,
	hall_S_thresh INT,
	Last_Updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

db.commit()
db.close()