import DB.DB_Back as db
import VLM_Control as VLM

from datetime import datetime
import random
import json

# for image adjustment
import os
from PIL import Image


## Normal Operation
def Norm_Product_Operation(ID, Shelf_Property, Product_ID, QTY, Operator_ID, Source="Website", project=None):
    """Logs a product operation (dispense or restock) and updates the database.
    Args:
        ID (int): The ID of the transaction.
        Shelf_Property (str): if Source is "Website", this is the Shelf_ID; if Source is not "Website" aka ESP, this is the Shelf Position.
        Product_ID (str): The ID of the product being operated on.
        QTY (int): The quantity of the product being dispensed or restocked.
        Operator_ID (str): The ID of the operator performing the operation.
        Source (str, optional): The source of the operation (e.g., "Website", "Mobile App"). Defaults to "Website".
        project (str, optional): The project name associated with the operation. Defaults to None.
    """
    if Source == "Website": 
        Shelf_ID = Shelf_Property
    else:
        Shelf_ID = db.Shelf_ID_From_Position(Shelf_Property)
    
    Current_Qty = db.Get_Product_on_Shelf_QTY(Shelf_ID, Product_ID)
    date = datetime.now()
    
    if QTY < 0:
        QTY_Removed = abs(QTY)
        QTY_Added = 0
    else:
        QTY_Removed = 0
        QTY_Added = QTY

    db.Add_Transaction_db(
        ID, Product_ID, Shelf_ID, date, QTY_Added, QTY_Removed, Operator_ID, Project_Name=project
    )

    db.Products_Shelves_Update_db(Shelf_ID, Product_ID, QTY + Current_Qty)
    
    db.log_event(
        "INFO",
        f"Product operation logged: ID={ID}, Product_ID={Product_ID}, Shelf_ID={Shelf_ID}, QTY_Added={QTY_Added}, QTY_Removed={QTY_Removed}, Operator_ID={Operator_ID}, Source={Source}, Project_Name={project}",
        "Server",
        transaction_type="PRODUCT_OPERATION",
        transaction_id=ID,
    )

def VLM_Product_Operation(Shelf_Pos, Product_ID, QTY, Operator_ID, project=None):
    """Logs a product operation (dispense or restock) and updates the database.
    Args:
        Shelf_ID (str): The ID of the shelf where the product is located.
        Product_ID (str): The ID of the product being operated on.
        QTY (int): The quantity of the product being dispensed or restocked.
        Operator_ID (str): The ID of the operator performing the operation.
        project (str, optional): The project name associated with the operation. Defaults to None.
    """
    Shelf_ID = db.Shelf_ID_From_Position(Shelf_Pos)
    Current_Qty = db.Get_Product_on_Shelf_QTY(Shelf_ID, Product_ID)
    date = datetime.now()
    ID = f"N-{date.day}-{date.month}-{date.minute}-{random.randint(1,9)}{random.randint(1,9)}{random.randint(1,9)}"

    if QTY < 0:
        QTY_Removed = abs(QTY)
        QTY_Added = 0
    else:
        QTY_Removed = 0
        QTY_Added = QTY

    db.Add_Transaction_db(
        ID, Product_ID, Shelf_ID, date, QTY_Added, QTY_Removed, Operator_ID, Project_Name=project
    )

    db.Products_Shelves_Update_db(Shelf_ID, Product_ID, QTY + Current_Qty)
    db.log_event(
        "INFO",
        f"VLM Product operation logged: ID={ID}, Product_ID={Product_ID}, Shelf_ID={Shelf_ID}, QTY_Added={QTY_Added}, QTY_Removed={QTY_Removed}, Operator_ID={Operator_ID}, Project_Name={project}",
        "Server",
        transaction_type="PRODUCT_OPERATION_VLM",
        transaction_id=ID,
    )
## Operator
def LogIn_Check(Username, Passw):
    """Checks if the provided username and password match an operator in the database.
    Args:
        Username (str): The username of the operator.
        Passw (str): The password of the operator.
    Returns:
        bool: True if the credentials are valid, False otherwise.
    """
    try:
        [Name, Salted_Passw, Salt, AccessLevel] = db.Operator_Login(Username)
    except:
        return "Invalid Username!", False, False

    Passw = db.Passw_Salter(Passw, Salt)

    if Passw == Salted_Passw:
        return True, Name, int(AccessLevel)
    else:
        return False, False, False


def First_Operator_Check():
    """Checks if there are any operators in the database.
    Returns:
        bool: True if no operators exist, False otherwise.
    """
    return not db.Operators_Exist()


## Products
def Add_Product(
    ID: str,
    Name: str,
    Description: str,
    Family_Name: str,
    Family_Item: str,
    Weight: float,
    ROP: int,
    OH: int,
    Length: float,
    Width: float,
    Height: float,
    Tags: list,
    Projects: list,
    Thumbnail,
    Photos: list,
):
    # ID: Product ID                                                (Text)
    # Name: Product Description                                     (Text)
    # Description: Product description                              (Text)
    # Family_Name: Product Family                                   (Text)
    # Family_Item: Category of Product in Family                    (Text)
    # Weight: Product's Weight (kg)                                 (Float)
    # ROP: Reorder Point                                            (Int)
    # Tags: Array or Tuple of product Tags                          (Array/Tuple)
    # Projects: Array or Tuple of projects used by the product      (Array/Tuple)
    # Photos: Array of Photo Paths

    # Adding Data into DB
    Projects = [proj for proj in Projects if isinstance(proj, str) and proj.strip()]
    db.Products_DB_Add(
        ID, Name, Description, Family_Name, Family_Item, Weight, ROP, OH, Length, Width, Height
    )

    Tags_Rows = [(ID, tag) for tag in Tags]
    db.TAGS_DB_Add(Tags_Rows)

    Projects_Rows = [(ID, proj) for proj in Projects]
    db.Projects_DB_Add(Projects_Rows)

    # Saving Photos
    Save_Uploaded_Photo(Thumbnail, Photos, ID)
    db.log_event(
        "INFO",
        f"Product added: ID={ID}, Name={Name}, Family_Name={Family_Name}, Family_Item={Family_Item}",
        "Server",
        transaction_type="PRODUCT_ADD",
        transaction_id=ID,
    )
    return True


def Save_Uploaded_Photo(Thumbnail, Photos, ID):
    """
    Saves the uploaded photos to the DB/Product_Pics/ID folder.
    The first photo is saved as Thumb.{format} and the rest are saved as 0.{format}, 1.{format}, etc.
    Args:
        Photos (file.getlist): List of uploaded photo files.
        ID (str): Product ID to create a folder for the photos.
    Returns:
        True if successful, or an error message if there was an issue.
    """
    try:
        os.mkdir(f"static/DB/Product_Pics/{ID}")
    except Exception as e:
        if e.strerror == "File exists":
            pass
        else:
            return e

    # Save the thumbnail
    format = (Thumbnail.filename).split(".")[-1]
    Thumbnail.save(f"static/DB/Compress_Temp/Thumb.{format}")  # Save the thumbnail temporarily
    # Compress and save the thumbnail
    thumb = Image.open(
        f"static/DB/Compress_Temp/Thumb.{format}"
    )  # Open the temporary thumbnail file
    thumb.save(
        f"static/DB/Product_Pics/{ID}/Thumb.{format}", quality=25
    )  # Compress the thumbnail to 25% quality
    os.remove(f"static/DB/Compress_Temp/Thumb.{format}")  # Remove the temporary thumbnail file

    for i, Photo in enumerate(Photos):
        format = (Photo.filename).split(".")[-1]
        Photo.save(f"static/DB/Compress_Temp/{i}.{format}")
        # Compress and save the photo
        img = Image.open(f"static/DB/Compress_Temp/{i}.{format}")
        img.save(f"static/DB/Product_Pics/{ID}/{i}.{format}", quality=80)
        os.remove(f"static/DB/Compress_Temp/{i}.{format}")  # Remove the temporary photo file

    # If we reach here, all photos were saved successfully
    return True


def Get_Product_Images(Product_ID):
    """
    Returns a list of image filenames available in static/DB/Product_Pics/{Product_ID}/.
    Args:
        Product_ID (str): The product ID to check for images.
    Returns:
        list: List of image filenames (e.g., ['Thumb.jpg', '0.jpg', '1.png']).
    """
    image_dir = f"static/DB/Product_Pics/{Product_ID}"
    images = []
    if os.path.exists(image_dir):
        images = [f for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    return images


def Unique_Product_Families_Get():
    """
    Reads all unique family names from the PRODUCTS table.
    Returns a list of family names, thumbnails and product ids of the first product found of the family.
    This is used for the home page where the photo would be the one gathered and will land on the page with that product ID.
    """
    Family_names = db.Unique_Family_Products_Get()
    Thumbnails, Products_ID = db.Home_Page_Families_Get(Family_names)

    if isinstance(Family_names, str):
        return Family_names, [], []

    return Family_names, Thumbnails, Products_ID


def Product_Read(Product_ID):
    Info = db.Products_Data_Read(Product_ID)
    Family_Products = db.Family_Products_Search(Info["Family_Name"])
    Projects = db.Product_Projects_Get(Product_ID)

    if Info is None:
        return "Product not found"
    return Info, Family_Products, Projects


def Products_Project_Search(project):
    """
    Searches for products associated with a specific project ID.
    Returns a list of products associated with the project.
    """
    Products_ID = db.Products_Project_Search(project)
    if not Products_ID:
        return "No products found for this project"

    Products = []
    for product_id in Products_ID:
        product_info = db.Products_Data_Read(product_id)
        if product_info:
            Products.append(product_info)

    return Products


def Website_Transaction(product_ids, operation, operator_id, QTY=1, project=None, Transaction_id=None):
    """
    Dispenses or restocks a product based on the operation type, and adds a transaction record in DB.
    Args:
        product_id (list): The ID of the product to dispense or restock.
        operation (str): The operation type, either 'dispense' or 'restock'.
        project (str, optional): The project ID associated with the operation. Defaults to None.
    Returns:
        JSON response indicating success or failure of the operation.
    """

    if operation not in ["dispense", "restock"]:
        return json.dumps({"status": "error", "message": "Invalid operation"}), 400

    # Physical Control of the VLM where the shelf is retrieved
    Shelf_IDs, Positions = db.Product_Shelf_Get(product_ids)

    if not Shelf_IDs:
        Shelf_IDs, Positions = db.Product_Shelf_Choose(product_ids)

    try:
        if operation == "dispense":
            Transaction = VLM.Products_Dispense(product_ids, Shelf_IDs, Positions)
            QTY = -QTY
        else:
            Transaction = VLM.Product_Restock(Positions)  # Restock must be a product based
        
        Transaction_id = db.Transaction_ID_Generator()
        
        if Transaction:
            for product_id, i in enumerate(product_ids):
                Norm_Product_Operation(
                    ID = Transaction_id,
                    Shelf_Property=Shelf_IDs[i],
                    Product_ID=product_id,
                    QTY=QTY,
                    Operator_ID=operator_id,
                    Source="Website",
                    project=project,
                )
            
            db.log_event(
                "INFO",
                f"Website {operation} operation successful for products {product_ids}",
                "Server",
                transaction_type="WEBSITE_TRANSACTION",
                transaction_id=Transaction_id,
            )
            return json.dumps({"status": "success", "message": "VLM operation successful"}), 200
        else:
            db.log_event(
                "ERROR",
                f"Website {operation} operation failed for products {product_ids}",
                "Server",
                transaction_type="WEBSITE_TRANSACTION",
                transaction_id=Transaction_id,
            )
            return json.dumps({"status": "error", "message": "VLM operation failed"}), 500

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}), 500


def Get_Product_Inventory(product_id):
    """
    Fetches inventory data for a product over time.
    Args:
        product_id (str): The ID of the product.
    Returns:
        dict: A dictionary containing dates and quantities.
    """
    try:
        inventory_records = db.Get_Product_Inventory_Records(product_id)
        dates = [record["Time"] for record in inventory_records]
        quantities = [record["On_Hand"] for record in inventory_records]
        operators = [record["Operator_ID"] for record in inventory_records]
        projects = [record["Project_Name"] for record in inventory_records]
        return {
            "dates": dates,
            "quantities": quantities,
            "operators": operators,
            "projects": projects,
        }
    except Exception as e:
        return str(e)


def Get_Logs(level=None, source=None, transaction_type=None, transaction_id=None, q=None, start=None, end=None, limit=50, offset=0):
    """Wrapper to DB.Get_Logs"""
    try:
        logs, total = db.Get_Logs(level=level, source=source, transaction_type=transaction_type, transaction_id=transaction_id, q=q, start=start, end=end, limit=limit, offset=offset)
        return logs, total
    except Exception as e:
        return [], 0


def Get_Log_Selectors():
    try:
        return db.Get_Log_Selectors()
    except Exception as e:
        return {'levels': [], 'sources': [], 'transaction_types': []}


# Other Backend Functions
def minimal_shelf_moves_variable_height(initial, final, shelf_heights, total_racks):
    """
    Plan minimal moves to rearrange shelves that occupy multiple rack slots.

    Args:
        initial: dict {shelf: start_rack}  # current bottom rack index
        final: dict {shelf: start_rack}    # desired bottom rack index
        shelf_heights: dict {shelf: height_in_racks}
        total_racks: int, total number of rack positions

    Returns:
        list of (shelf, from_start, to_start)
    """
    moves = []

    # Represent rack occupancy as an array: 0 = empty, else = shelf label
    racks = [0] * (total_racks + 1)  # 1-indexed for clarity

    def occupy(shelf, start, value):
        """Mark racks as occupied/unoccupied by a shelf."""
        for i in range(start, start + shelf_heights[shelf]):
            racks[i] = value

    # Initialize occupancy
    for shelf, start in initial.items():
        occupy(shelf, start, shelf)

    def is_space_free(start, size):
        """Check if contiguous racks [start : start+size-1] are empty."""
        if start + size - 1 > total_racks:
            return False
        return all(racks[i] == 0 for i in range(start, start + size))

    def find_temp_space(size):
        """Find first contiguous empty segment large enough."""
        for s in range(1, total_racks - size + 2):
            if is_space_free(s, size):
                return s
        return None

    def move(shelf, to_start):
        from_start = initial[shelf]
        occupy(shelf, from_start, 0)
        occupy(shelf, to_start, shelf)
        initial[shelf] = to_start
        moves.append((shelf, from_start, to_start))

    # Process shelves
    for shelf in list(initial.keys()):
        while initial[shelf] != final[shelf]:
            target = final[shelf]
            size = shelf_heights[shelf]

            # Check if target space free
            if is_space_free(target, size):
                move(shelf, target)
            else:
                # Find who blocks the target range
                blocked = set(racks[i] for i in range(target, target + size) if racks[i] != 0)
                blocking_shelf = blocked.pop() if blocked else None

                if not blocking_shelf:
                    continue  # should not happen

                # Move blocker temporarily
                temp_start = find_temp_space(shelf_heights[blocking_shelf])
                if temp_start is None:
                    raise RuntimeError(f"No space to move blocking shelf {blocking_shelf}.")
                move(blocking_shelf, temp_start)

                # Retry moving the current shelf (loop continues)
                continue

    return moves
