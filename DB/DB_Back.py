import sqlite3
import queue
import bcrypt

# Simple connection pool
class ConnectionPool:
    def __init__(self, db_path, pool_size=5):
        self.db_path = db_path
        self.pool = queue.Queue(maxsize=pool_size)
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            self.pool.put(conn)

    def get_connection(self):
        return self.pool.get()

    def return_connection(self, conn):
        self.pool.put(conn)

pool = ConnectionPool("DB/DB.db")

# Context manager for connections
class DBConnection:
    def __enter__(self):
        self.conn = pool.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        pool.return_connection(self.conn)

# def get_db_connection():
#     """Create a new SQLite connection for the current thread."""
#     db = sqlite3.connect("DB/DB.db")
#     # db.row_factory = sqlite3.Row
#     return db

###### NORMAL OPERATION OF VLMS:
def Get_Product_on_Shelf_QTY(Product_ID, Shelf_ID):
    """Get current quantity of product on shelf.
    Args:
        Product_ID (str): The unique identifier of the product.
        Shelf_ID (str): The unique identifier of the shelf.
    Returns:
        int: The quantity of the product on the shelf. Returns 0 if not found.
        """
    
    with DBConnection() as db:
        cursor = db.cursor()
        cursor.execute(
            "SELECT Quantity FROM PRODUCTS_SHELVES WHERE Product_ID = ? AND Shelf_ID = ?",
            (Product_ID, Shelf_ID),
        )
        Qty = cursor.fetchone()
        return Qty[0] if Qty else 0

def Product_Shelf_Get(Product_ID):
    """Get the shelf ID where the product is located.
    Args:
        Product_ID (list): The unique identifier of the product or a list of product IDs.
    Returns:
        list: A list of shelf IDs where the product(s) is/are located.
    """
    with DBConnection() as db:
    
        cursor = db.cursor()
        Shelf_IDs = []
        Positions = []
        
        # If Product_ID is a list, loop through each IDs
        for pid in Product_ID:
            cursor.execute(
                "SELECT Shelf_ID, Pos FROM PRODUCTS_SHELVES WHERE Product_ID = ? ORDER BY SpaceLeft DESC",
                (pid,),
            )
            Shelf_ID_loop = cursor.fetchone()

            if Shelf_ID_loop:
                
                Shelf_IDs.append(Shelf_ID_loop[0])
                Positions.append(Shelf_ID_loop[1])
            
        return Shelf_IDs, Positions if Shelf_IDs else (None, None)

def Product_Shelf_Choose(Product_IDs):
    """Choose the best shelf for dispensing/restocking based on quantity and weight.
    Args:
        Product_ID (list): The unique identifier of the product.
    Returns:
        best_shelf[0]: list: A list containing the best shelf ID.
        best_shelf[1]: list: A list containing the best shelf position.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        best_shelf = None
        Product_ID = Product_IDs[0]  # Assuming we are choosing shelf for the first product in the list
       # Sequence: 1. Get Product info 2. Get projects associated with product 3. Get other products on those projects 4. Get shelves associated with those products if not found

        cursor.execute("SELECT * FROM PRODUCTS WHERE ID = ?", (Product_ID,))
        product = cursor.fetchone()
        if not product:
            return None
        cursor.execute("SELECT * FROM PRODUCT_PROJECTS WHERE Product_ID = ?", (Product_ID,))
        
        project_names = cursor.fetchall()
        if project_names:
            project_names = [project[1] for project in project_names]

            placeholders = ', '.join('?' * len(project_names))
            query = f"SELECT Product_ID FROM PRODUCT_PROJECTS WHERE Project IN ({placeholders})"
            cursor.execute(query, project_names)
            
            related_products = cursor.fetchall()
            if related_products:
                related_products = [rp[0] for rp in related_products if rp[0] != Product_ID]
                
                placeholders = ', '.join('?' * len(related_products))
                query = f"SELECT Shelf_ID FROM PRODUCTS_SHELVES WHERE Product_ID IN ({placeholders})"
                cursor.execute(query, related_products)
                
                shelf_ids = cursor.fetchall()
                if shelf_ids:
                    shelf_ids = [shelf[0] for shelf in shelf_ids]

                    placeholders = ', '.join('?' * len(shelf_ids))
                    query = f"SELECT ID, Pos, Weight, SpaceLeft FROM SHELVES WHERE ID IN ({placeholders}) ORDER BY SpaceLeft DESC, Weight ASC"
                    cursor.execute(query, shelf_ids)
                    best_shelf = cursor.fetchone()
                    if best_shelf:
                        return [best_shelf[0]], [best_shelf[1]]

        # If no projects or project logic failed, look for family 
        if not best_shelf:
            cursor.execute("SELECT Family_Name FROM PRODUCTS WHERE ID = ?", (Product_ID,))
            family_name = cursor.fetchall()
            if family_name:
                family_name = [fn[0] for fn in family_name]
                placeholders = ', '.join('?' * len(family_name))
                query = f"SELECT ID FROM PRODUCTS WHERE Family_Name IN ({placeholders})"

                cursor.execute(query, family_name)
                family_products = cursor.fetchall()
                
                if family_products:
                    family_products = [fp[0] for fp in family_products if fp[0] != Product_ID]
                    
                    placeholders = ', '.join('?' * len(family_products))
                    query = f"SELECT Shelf_ID FROM PRODUCTS_SHELVES WHERE Product_ID IN ({placeholders})"
                    cursor.execute(query, family_products)
                    
                    shelf_ids = cursor.fetchall()
                    if shelf_ids:
                        shelf_ids = [shelf[0] for shelf in shelf_ids]

                        placeholders = ', '.join('?' * len(shelf_ids))
                        query = f"SELECT ID, Pos, Weight, SpaceLeft FROM SHELVES WHERE ID IN ({placeholders}) ORDER BY SpaceLeft DESC, Weight ASC"
                        cursor.execute(query, shelf_ids)
                        best_shelf = cursor.fetchone()
                        if best_shelf:
                            return [best_shelf[0]], [best_shelf[1]]

        # Fallback: If no related shelves found, pick the best from all shelves
        if not best_shelf:
            cursor.execute("SELECT ID, Pos FROM SHELVES ORDER BY SpaceLeft DESC, Weight ASC")
            best_shelf = cursor.fetchone()
            if best_shelf:
                return [best_shelf[0]], [best_shelf[1]]

def Get_Product_Inventory_Records(product_id: str):
    """
    Fetches inventory records for a specific product from the TRANSACTIONS table.
    Args:
        product_id (str): The ID of the product to fetch inventory records for.
    Returns:
        list: A list of dictionaries containing inventory records for the product.
    """

    with DBConnection() as db:
        cursor = db.cursor()
        cursor.execute(
            """SELECT Time, Quantity_Added, Quantity_Removed, Operator_ID, Project_Name, Shelf_ID
               FROM TRANSACTIONS
               WHERE Product_ID = ?
               ORDER BY Time DESC""",
            (product_id,),
        )
        rows = cursor.fetchall()
        records = []
        cursor.execute(
            """
                SELECT OH FROM PRODUCTS WHERE ID = ?
            """,
            (product_id,)
        )
        oh = cursor.fetchone()
        for row in rows:
            records.append({
                "Time": row[0],
                "On_Hand": oh[0] if len(records) == 0 else records[-1]["On_Hand"] - row[2] + row[1],
                "Quantity_Added": row[1],
                "Quantity_Removed": row[2],
                "Operator_ID": row[3],
                "Project_Name": row[4],
                "Shelf_ID": row[5]
            })
        return records


### Transactions section
def Add_Transaction_db(ID, Product_ID, Shelf_ID, Time, Quantity_Added, Quantity_Removed, Operator_ID, Project_Name):
    """
    Adds a transaction to the TRANSACTIONS table.
    Args:
        ID (str): Unique identifier for the transaction.
        Product_ID (str): ID of the product involved in the transaction.
        Shelf_ID (str): ID of the shelf where the transaction occurred.
        Time (str): Timestamp of the transaction.
        Quantity_Added (int): Quantity of product added in the transaction.
        Quantity_Removed (int): Quantity of product removed in the transaction.
        Operator_ID (str): ID of the operator who performed the transaction.
    Returns:
        bool: True if the transaction was added successfully, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO TRANSACTIONS VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (ID, Product_ID, Project_Name,Shelf_ID, Time, Quantity_Added, Quantity_Removed, Operator_ID),
            )
            db.commit()
        except Exception as e:
            return e
        return True

def Transaction_ID_Generator():
    """
    Generates a new unique transaction ID.
    Returns:
        str: A new unique transaction ID.
    """
    import uuid
    id = str(uuid.uuid4().hex)[:8]

    return int(id, 16)

def Products_Shelves_Update_db(Shelf_ID, Product_ID, Quantity):
    """
    Updates the quantity of a product on a shelf in the PRODUCTS_SHELVES table.
    Args:
        Shelf_ID (str): ID of the shelf where the product is located.
        Product_ID (str): ID of the product to update.
        Quantity (int): New quantity of the product on the shelf.
    Returns:
        bool: True if the update was successful, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO PRODUCTS_SHELVES VALUES(?, ?, ?)",
                (Shelf_ID, Product_ID, Quantity),
            )
            Shelves_qty_Update(db)
            Shelves_Weight_Update(db)
            Shelves_SpaceLeft_Update(db)
            Products_qty_Update(db)
            db.commit()
        except Exception as e:
            return e
    return True

def Shelves_qty_Update(db):
    """
    Updates the quantity of products on each shelf in the SHELVES table.
    This function calculates the total quantity of products on each shelf
    by summing the quantities from the PRODUCTS_SHELVES table.
    Args:
        db (sqlite3.Connection): The database connection object.
    Returns:
        bool: True if the update was successful, otherwise an error message.
    """
    cursor = db.cursor()
    cursor.execute(
        """UPDATE SHELVES
           SET Quantity = (
               SELECT SUM(Quantity)
               FROM PRODUCTS_SHELVES
               WHERE PRODUCTS_SHELVES.Shelf_ID = SHELVES.ID
           );"""
    )
    db.commit()
    return True

def Shelves_Weight_Update(db):
    """Updates the weight of products on each shelf in the SHELVES table.
    This function calculates the total weight of products on each shelf
    by summing the weights from the PRODUCTS_SHELVES table.
    Args:
        db (sqlite3.Connection): The database connection object.
    Returns:
        bool: True if the update was successful, otherwise an error message.
    """
    cursor = db.cursor()
    cursor.execute(
        """UPDATE SHELVES
           SET Weight = (
               SELECT SUM(PRODUCTS.Weight * PRODUCTS_SHELVES.Quantity)
               FROM PRODUCTS_SHELVES
               JOIN PRODUCTS ON PRODUCTS_SHELVES.Product_ID = PRODUCTS.ID
               WHERE PRODUCTS_SHELVES.Shelf_ID = SHELVES.ID
           );"""
    )
    db.commit()
    return True

def Shelves_SpaceLeft_Update(db):
    """Updates the space left on each shelf in the SHELVES table.
    Args:
        db (sqlite3.Connection): The database connection object.
    Returns:
        bool: True if the update was successful, otherwise an error message.
    """
    from shared_states import shelf_properties
    cursor = db.cursor()
    try:
        # Calculate shelf area (width * depth)
        shelf_area = shelf_properties['width'] * shelf_properties['depth']
        
        cursor.execute(
            f"""UPDATE SHELVES
               SET SpaceLeft = 100 - COALESCE((
                   SELECT (SUM(Length * Width * Quantity) / {shelf_area}) * 100
                   FROM PRODUCTS_SHELVES
                   JOIN PRODUCTS ON PRODUCTS_SHELVES.Product_ID = PRODUCTS.ID
                   WHERE PRODUCTS_SHELVES.Shelf_ID = SHELVES.ID
               ), 100)  -- Default to 100% used if no products (avoids NULL)
               WHERE ID IN (
                   SELECT Shelf_ID FROM PRODUCTS_SHELVES
               );"""  # Only update shelves with products
        )
        db.commit()
        return True
    except KeyError as e:
        return f"Missing shelf property: {e}"
    except Exception as e:
        return f"Update failed: {e}"

def Products_qty_Update(db):
    """Updates the on-hand (OH) quantity of products in the PRODUCTS table.
    This function calculates the total on-hand quantity of each product
    by summing the quantities from the PRODUCTS_SHELVES table.
    Args:
        db (sqlite3.Connection): The database connection object.
    Returns:
        bool: True if the update was successful, otherwise an error message.
    """
    cursor = db.cursor()
    cursor.execute(
        """UPDATE PRODUCTS
           SET OH = (
               SELECT SUM(Quantity)
               FROM PRODUCTS_SHELVES
               WHERE PRODUCTS_SHELVES.Product_ID = PRODUCTS.ID
           );"""
    )
    db.commit()
    return True

 
###### ADDING NEW SHELVES INTO DB:
def Shelves_DB_Add(ID, Pos, Weight=0, Quantity=0, SpaceLeft=100, RacksAvailable=1):
    """Adds a new shelf to the SHELVES table.
    Args:
        ID (str): Unique identifier for the shelf.
        Pos (str): Position of the shelf.
        Weight (float): Weight capacity of the shelf.
        Quantity (int): Initial quantity of products on the shelf.
        SpaceLeft (int): Initial space left on the shelf.
        RacksAvailable (int): Initial number of racks above the shelf, default 1.
    Returns:
        bool: True if the shelf was added successfully, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO SHELVES VALUES(?, ?, ?, ?, ?, ?)",
                (ID, Pos, Weight, Quantity, SpaceLeft, RacksAvailable),
            )
            db.commit()
        except Exception as e:
            return e

        return True

def Shelves_DB_Pos_Update(ID, Pos):
    """Updates the position of a shelf in the SHELVES table.
    Args:
        ID (str): Unique identifier for the shelf.
        Pos (str): New position of the shelf.
    Returns:
        bool: True if the position was updated successfully, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE SHELVES SET Pos = ? WHERE ID = ?", (Pos, ID))
            db.commit()
        except Exception as e:
            return e
        else:
            return True

def Shelves_DB_Pos_Get(ID):
    """Gets the position of a shelf from the SHELVES table.
    Args:
        ID (str): Unique identifier for the shelf.
    Returns:
        str: Position of the shelf if found, otherwise None.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute("SELECT Pos FROM SHELVES WHERE ID = ?", (ID,))
            Pos = cursor.fetchone()
            return Pos[0] if Pos else None
        except Exception as e:
            return e


def Shelf_ID_From_Position(Pos):
    """Gets the shelf ID from its position in the SHELVES table.
    Args:
        Pos (str): Position of the shelf.
    Returns:
        str: ID of the shelf if found, otherwise None.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute("SELECT ID FROM SHELVES WHERE Pos = ?", (Pos,))
            Shelf_ID = cursor.fetchone()
            return Shelf_ID[0] if Shelf_ID else None
        except Exception as e:
            return e


###### ADDING NEW PRODUCTS INTO DB:
def Products_DB_Add(ID, Name, Description, Family_Name, Family_Item, Weight, ROP, OH, Length, Width, Height):
    """Adds a new product to the PRODUCTS table.
    Args:
        ID (str): Unique identifier for the product.
        Name (str): Name of the product.
        Description (str): Description of the product.
        Family_Name (str): Family name of the product.
        Family_Item (str): Category of the product within its family.
        Weight (float): Weight of the product in kilograms.
        ROP (int): Reorder point for the product.
        OH (int): On-hand quantity of the product.
        Length (float): Length of the product in centimeters.
        Width (float): Width of the product in centimeters.
        Height (float): Height of the product in centimeters.
    Returns:
        bool: True if the product was added successfully, otherwise an error message.
    """
    with DBConnection() as db:  
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT OR REPLACE INTO PRODUCTS VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ID, Name, Description, Family_Name, Family_Item, Weight, ROP, OH, Length, Width, Height),
            )
            db.commit()
        except Exception as e:
            return e
    return True

def TAGS_DB_Add(row):
    """Adds tags to the PRODUCT_TAGS table.
    Args:
        row (list): A list of tuples, each containing a product ID and a tag.
    Returns:
        bool: True if the tags were added successfully, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.executemany("INSERT OR IGNORE INTO PRODUCT_TAGS VALUES(?, ?)", row)
            db.commit()
        except Exception as e:
            return e
    return True

def Projects_DB_Add(row):
    """Adds projects to the PRODUCT_PROJECTS table.
    Args:
        row (list): A list of tuples, each containing a product ID and a project.
    Returns:
        bool: True if the projects were added successfully, otherwise an error message.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.executemany("INSERT OR IGNORE INTO PRODUCT_PROJECTS VALUES(?, ?)", row)
            db.commit()
        except Exception as e:
            return e
    return True

def Products_Data_Read(Product_ID):
    """
    Reads product information from the PRODUCTS table based on Product_ID.
    Returns a dictionary with product details.
    
    Args:
        Product_ID (str): The unique identifier of the product.
    Returns:
        dict: A dictionary containing product details such as ID, Name, Description,
              Family_Name, Family_Item, Weight, ROP (Reorder Point), and OH (On-Hand quantity).
        None: If the product is not found.
    """
    with DBConnection() as db:
        try:    
            cursor = db.cursor()
            cursor.execute("SELECT * FROM PRODUCTS WHERE ID = ?", (Product_ID,))
            row = cursor.fetchone()
            if row:
                return {
                    "ID": row[0],
                    "Name": row[1],
                    "Description": row[2],
                    "Family_Name": row[3],
                    "Family_Item": row[4],
                    "Weight": row[5],
                    "ROP": row[6],
                    "OH": row[7]
                }
            else:
                return None
        except Exception as e:
            print(str(e))

def Family_Products_Search(Family):
    """
    Reads all unique family names from the PRODUCTS table.
    Returns a list of family names and a dictionary of product IDs.
    """
    with DBConnection() as db:
        try:
            cursor = db.cursor()
            data = cursor.execute("SELECT ID, Family_Item FROM PRODUCTS WHERE Family_Name = ?;", (Family,))
            rows = data.fetchall()
            if not rows:
                return None, None
            else:
                return rows
        
        except Exception as e:
            print(str(e))

def Unique_Family_Products_Get():
    """
    Reads all unique family names from the PRODUCTS table.
    Returns a list of family names.
    """
    try:
        with DBConnection() as db_conn:
            cursor = db_conn.cursor()
            cursor.execute("SELECT DISTINCT Family_Name FROM PRODUCTS ORDER BY Family_Name")
            family_names = [row[0] for row in cursor.fetchall()]
            return family_names
    except Exception as e:
        print(str(e))

def Home_Page_Families_Get(family_names):
    """
    Reads product IDs and thumbnails for the given family names.
    Returns a list of thumbnails and IDs.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        Thumbnails = []
        IDs = []
        for family in family_names:
            cursor.execute("SELECT ID FROM PRODUCTS WHERE Family_Name = ? LIMIT 1", (family,))
            product_id = cursor.fetchone()
            if product_id:
                Thumbnails.append(f"DB/Product_Pics/{product_id[0]}/Thumb.jpg")
                IDs.append(product_id[0])
            else:
                Thumbnails.append(None)
                IDs.append(None)
        return Thumbnails, IDs

def Products_Family_Search(text):
    """
    Reads all unique family names from the PRODUCTS table.
    Returns a list of family names.
    Used in the family name api when creating a new product.
    The text is used to filter family names that start with the given text.
    Args:
        text (str): The text to filter family names.
    Returns:
        list: A list of family names that start with the given text.
    """
    try:
        with DBConnection() as db_conn:
            cursor = db_conn.cursor()
            text = f"%{text}%"
            cursor.execute("SELECT DISTINCT Family_Name FROM PRODUCTS WHERE Family_Name LIKE ? ORDER BY Family_Name", (text,))
        family_names = [row[0] for row in cursor.fetchall()]
        return family_names
    except Exception as e:
        print(str(e))


def Products_Projects_Search(text):
    """
    Reads all unique project names from the PRODUCT_PROJECTS table.
    Returns a list of project names.
    Used in the project name api when creating a new product.
    The text is used to filter project names that start with the given text.
    
    Args:
        text (str): The text to filter project names.
    Returns:
        list: A list of project names that start with the given text.
    """
    try:
        with DBConnection() as db_conn:
            cursor = db_conn.cursor()
            text = f"%{text}%"
            cursor.execute("SELECT DISTINCT Project FROM PRODUCT_PROJECTS WHERE Project LIKE ? ORDER BY Project", (text,))
            projects = [row[0] for row in cursor.fetchall()]
            return projects
    except Exception as e:
        print(str(e))


def Product_Projects_Get(Product_ID):
    """
    Reads all projects associated with a product from the PRODUCT_PROJECTS table.
    Returns a list of projects.
    
    Args:
        Product_ID (str): The unique identifier of the product.
    Returns:
        list: A list of projects associated with the product.
        None: If no projects are found for the product.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT Project FROM PRODUCT_PROJECTS WHERE Product_ID = ?", (Product_ID,))
            rows = cursor.fetchall()
            if rows:
                return [row[0] for row in rows]
            else:
                return None
    except Exception as e:
        print(str(e))

def Products_Project_Search(Project):
    """
    Searches for products associated with a specific project in the PRODUCT_PROJECTS table.
    Returns a list of product IDs associated with the project.
    
    Args:
        Project (str): The name of the project to search for.
    Returns:
        list: A list of product IDs associated with the project.
        None: If no products are found for the project.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT Product_ID FROM PRODUCT_PROJECTS WHERE Project = ?", (Project,))
            IDs = cursor.fetchall()
            if IDs:
                return [row[0] for row in IDs]
            else:
                return None
    except Exception as e:
        print(str(e))


def Get_Unique_Projects():
    """
    Fetches all unique project names from the PRODUCT_PROJECTS table.
    Returns a list of project names.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT DISTINCT Project FROM PRODUCT_PROJECTS ORDER BY Project")
            projects = [row[0] for row in cursor.fetchall()]
            return projects if projects else []
    except Exception as e:
        print(str(e))

def Get_Products():
    """
    Fetches all product IDs data from the PRODUCTS table.
    Returns a dictionary of product IDs and their associated data.
    The data:
        - Name
        - Weight
        - Length
        - Width
        - Height
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT ID, Name, Weight, Length, Width, Height FROM PRODUCTS ORDER BY ID")
            
            products = cursor.fetchall()
            products_data = {}
            for i in range(len(products)):
                products_data[products[i][0]] = {
                    
                    "Name": products[i][1],
                    "Weight": products[i][2],
                    "Length": products[i][3],
                    "Width": products[i][4],
                    "Height": products[i][5]
                }
            return products_data if products_data else {}
    except Exception as e:
        print(str(e))

def Get_Products_Projects():
    """
    Fetches all project names data from the PRODUCT_PROJECTS table.
    Returns a dictionary of product IDs and their associated project names.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT Project, Product_ID FROM PRODUCT_PROJECTS")
            projects = cursor.fetchall()
            products_projects = {}
            for i in range(len(projects)):
                if projects[i][1] in products_projects:
                    products_projects[projects[i][1]].append(projects[i][0])
                else:
                    products_projects[projects[i][1]] = [projects[i][0]]
            return products_projects if products_projects else {}
    except Exception as e:
        print(str(e))

###### Operator DB Management
def Operators_Exist():
    """
    Checks if any operators exist in the OPERATORS table.
    Returns:
        bool: True if operators exist, False otherwise.
    """
    with DBConnection() as db:
        cursor = db.cursor()
    
        cursor.execute("SELECT 1 FROM OPERATORS LIMIT 1")
        return cursor.fetchone() is not None

def Operator_Add(ID, Name, Username, Passw, Access_Level=1):
    """
    Adds a new operator to the OPERATORS table.
    Args:
        ID (str): The unique identifier for the operator.
        Name (str): The name of the operator.
        Username (str): The username for the operator.
        Passw (str): The password for the operator.
    Returns:
        bool: True if the operator was added successfully, otherwise an error message.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            [Hashed_Passw, Salt] = Passw_Hasher(Passw)
        
            cursor.execute(
                    "INSERT INTO OPERATORS VALUES(?, ?, ?, ?, ?, ?)",
                    (ID, Name, Username, Hashed_Passw, Salt, Access_Level),
                )
            db.commit()
    except Exception as e:
        return e


def Operator_Login(Username):
    """
    Queries the OPERATORS table for the given username.
    Args:
        Username (str): The username to query.
    Returns:
        tuple: A tuple containing the hashed password and salt for the operator.
    Raises:
        Exception: If the username is not found in the database.
    """
    with DBConnection() as db:
        cursor = db.cursor()
    
        cursor.execute(
            "SELECT Name, Password, Password_Salt, Access_Level FROM OPERATORS WHERE Username = ?", (Username,)
        )
        result = cursor.fetchone()
        if result:
            return result[0], result[1], result[2], result[3]
        else:
            raise Exception("Username not found")

def Operator_ID_Query(ID):
    """
    Queries the OPERATORS table for the given operator ID.
    Args:
        ID (str): The operator ID to query.
    Returns:
        tuple: A tuple containing the operator's name, username.
    Raises:
        Exception: If the operator ID is not found in the database.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
        
            cursor.execute(
                "SELECT Name, Username FROM OPERATORS WHERE ID = ?", (ID,)
            )
            result = cursor.fetchone()

            if result:
                return result[0], result[1]
            else:
                return None
                # raise Exception("Operator ID not found")
                
    except Exception as e:
        return str(e)

def Passw_Hasher(Passw: str):
    """
    Hashes the password using bcrypt and returns the hashed password and salt.
    Args:
        Passw (str): The password to hash.
    Returns:
        tuple: A tuple containing the hashed password and the salt used for hashing.
    """

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(Passw.encode("utf-8"), salt).decode("utf-8")
    return hashed, salt.decode("utf-8")

def Passw_Salter(data: str, salt: str):
    """
    Salts the given data using the provided salt.
    Args:
        data (str): The data to salt.
        salt (str): The salt to use for salting the data.
    Returns:
        str: The salted data.
    """
    new = bcrypt.hashpw(data.encode("utf-8"), salt.encode("utf-8")).decode("utf-8")
    return new

### VLM Configuration Logging
def VLM_Update_Configuration(normal_speed,
                        approach_speed,
                        steps_per_floor,
                        stop_pulse,
                        for_pulse,
                        back_pulse,
                        collect_time,
                        return_time, hall_N_thresh, hall_S_thresh):
    """
    Updates the VLM configuration parameters in the VLM_CONFIG table.
    Args:
        normal_speed (int): Normal speed.
        approach_speed (int): Approach speed.
        stop_pulse (int): Stop pulse duration.
        for_pulse (int): Forward pulse duration.
        back_pulse (int): Backward pulse duration.
        collect_time (int): Collect time duration.
        return_time (int): Return time duration.
    Returns:
        bool: True if the configuration was updated successfully, otherwise an error message.
    """ 
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute(
                """INSERT INTO  VLM_CONFIG (Normal_Speed, Approach_Speed, Steps_Per_Floor, Stop_Pulse, For_Pulse, Back_Pulse, Collect_Time, Return_Time, hall_N_thresh, hall_S_thresh, Last_Updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   """,
                (normal_speed,
                 approach_speed,
                    steps_per_floor,
                 stop_pulse,
                 for_pulse,
                 back_pulse,
                 collect_time,
                 return_time,
                 hall_N_thresh,
                 hall_S_thresh),
            )
            db.commit()
        except Exception as e:
            return e


def VLM_Get_Configuration():
    """
    Retrieve the current VLM configuration as a dictionary.
    Returns:
        dict: {'normal_delay', 'approaching_delay', 'stop_pulse', 'for_pulse', 'back_pulse', 'collect_time', 'return_time'}
        or None if not found / on error.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute('SELECT Normal_Speed, Approach_Speed, Steps_Per_Floor, Stop_Pulse, For_Pulse, Back_Pulse, Collect_Time, Return_Time, hall_N_thresh, hall_S_thresh, Last_Updated FROM VLM_CONFIG LIMIT 1')
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'Normal_Speed': row[0],
                'Approach_Speed': row[1],
                'Steps_Per_Floor': row[2],
                'Stop_Pulse': row[3],
                'For_Pulse': row[4],
                'Back_Pulse': row[5],
                'Collect_Time': row[6],
                'Return_Time': row[7],
                'hall_N_thresh': row[8],
                'hall_S_thresh': row[9],
                'Last_Updated': row[10]
            }
    except Exception as e:
        print(f'VLM_Get_Configuration failed: {e}')
        return None


def Get_Logs(level=None, source=None, transaction_type=None, transaction_id=None, q=None, start=None, end=None, limit=50, offset=0):
    """Query logs with optional filters and pagination.
    Returns: (rows, total_count)
    """
    with DBConnection() as db:
        cursor = db.cursor()
        where = []
        params = []
        if level:
            where.append("Level = ?")
            params.append(level)
        if source:
            where.append("Source = ?")
            params.append(source)
        if transaction_type:
            where.append("Transaction_Type = ?")
            params.append(transaction_type)
        if transaction_id:
            where.append("Transaction_ID = ?")
            params.append(transaction_id)
        if q:
            where.append("Message LIKE ?")
            params.append(f"%{q}%")
        if start:
            where.append("Timestamp >= ?")
            params.append(start)
        if end:
            where.append("Timestamp <= ?")
            params.append(end)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        # total count
        count_q = f"SELECT COUNT(*) FROM LOGS {where_sql}"
        cursor.execute(count_q, params)
        total = cursor.fetchone()[0]

        q_str = f"SELECT ID, Timestamp, Transaction_Type, Transaction_ID, Level, Source, Message FROM LOGS {where_sql} ORDER BY Timestamp DESC LIMIT ? OFFSET ?"
        cursor.execute(q_str, params + [limit, offset])
        rows = cursor.fetchall()
        # convert to list of dicts
        logs = []
        for r in rows:
            logs.append({
                'id': r[0],
                'timestamp': r[1],
                'transaction_type': r[2],
                'transaction_id': r[3],
                'level': r[4],
                'source': r[5],
                'message': r[6]
            })
        return logs, total


def Get_Log_Selectors():
    """Return distinct values for Level, Source, Transaction_Type to populate filters."""
    with DBConnection() as db:
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT Level FROM LOGS")
        levels = [r[0] for r in cursor.fetchall() if r[0]]
        cursor.execute("SELECT DISTINCT Source FROM LOGS")
        sources = [r[0] for r in cursor.fetchall() if r[0]]
        cursor.execute("SELECT DISTINCT Transaction_Type FROM LOGS")
        types = [r[0] for r in cursor.fetchall() if r[0]]
        return {'levels': levels, 'sources': sources, 'transaction_types': types}



###### ADDING LOGGING FUNCTIONALITY
def log_event(level, message, source ,transaction_type=None, transaction_id=None):
    """
    Logs an event to the LOGS table.
    Args:
        level (str): Log level (e.g., 'INFO', 'ERROR', 'WARNING').
        message (str): Log message.
        source (str): Source of the log event (ESP32 or Server).
        transaction_type (str, optional): Type of transaction (e.g., 'ADD', 'REMOVE').
        transaction_id (str, optional): ID of the related transaction.
    """
    with DBConnection() as db:
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO LOGS (Level, Message, Source, Transaction_Type, Transaction_ID) VALUES (?, ?, ?, ?, ?)",
                (level, message, source, transaction_type, transaction_id)
            )
            db.commit()
        except Exception as e:
            print(f"Logging failed: {e}")  # Fallback if logging itself fails

### Forecast Projects
def Forecast_Project_Get():
    """
    Fetches all forecast projects from the FORECASTS table.
    Returns a list of project names.
    """
    try:
        with DBConnection() as db:
            cursor = db.cursor()
            cursor.execute("SELECT UNIQUE ID Product_ID, Project_Name, Shelf_ID, Time, Quantity_Removed FROM TRANSACTIONS")
            projects = [row[0] for row in cursor.fetchall()]
            return projects if projects else []
    except Exception as e:
        print(str(e))


