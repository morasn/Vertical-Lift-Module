import json
from Websocket_Server import WS_Send_sync
from DB.DB_Back import log_event, Transaction_ID_Generator

from shared_states import current_level

def Products_Dispense(Product_IDs, Shelf_IDs, Positions):
    """
    Interacts with the Arduino to dispense or restock a product.
    Args:
        Product_IDs (list): The ID of the product to dispense or restock.
        Shelf_IDs (list): The ID of the shelf where the product is located.
        Positions (list): The positions of the products on the shelves.
    Returns:
        JSON response indicating success or failure of the operation.
    """
    global current_level

    Differences = []
    
    for shelf_id in Shelf_IDs:
        Differences.append(
            abs(int(shelf_id[1:3]) - current_level)
        )  # Extract level from shelf ID (assuming format 'SLLXX')

    # Get the closest to the current level
    min_idx = Differences.index(min(Differences))
    Shelf_IDs.insert(0, Shelf_IDs.pop(min_idx))
    Product_IDs.insert(0, Product_IDs.pop(min_idx))
    Differences.insert(0, Differences.pop(min_idx))

    floors = []
    products = []
    orders_per_floor = []

    for shelf_id, product_id, position in zip(Shelf_IDs, Product_IDs, Positions):
        floor = position  # e.g. 'S01' from 'S01XX'
        if floor in floors:
            idx = floors.index(floor)
            products[idx].append(product_id)
            orders_per_floor[idx] += 1
        else:
            floors.append(floor)
            products.append([product_id])
            orders_per_floor.append(1)

    # Construct the JSON payload
    # Implement Transaction ID generation as needed
    transaction_id = Transaction_ID_Generator()
    payload = {
        "code": 100,
        "Iter": len(floors),
        "Floors": floors,
        "OrdersPerFloor": orders_per_floor,
        "transaction_id": transaction_id,
    }

    WS_Send_sync(json.dumps(payload))

    current_level = int(floors[-1][1:3])  # Update current level to the last floor in the list

    log_event(
        "INFO", "Dispense command sent.", transaction_type="DISPENSE", transaction_id=transaction_id
    )

    return {"status": "success", "message": "Dispense command sent."}


def Product_Restock(Position):
    """
    Interacts with ESP to restock the product on the shelf
    Arg:
        Position (list): The position of the product on the shelf. (List with one element) e.g. ['F01', 'B02']
    return:
        bool:
    """
    global current_level
    transaction_id = Transaction_ID_Generator()
    payload = {"code": 101, "Floor": Position[0], "transaction_id": transaction_id}

    Stat = WS_Send_sync(json.dumps(payload))
    if Stat:
        log_event(
            "INFO",
            "Restock command sent.",
            transaction_type="RESTOCK",
            transaction_id=transaction_id,
        )
        current_level = int(Position[0][1:3])  # Update current level to the first floor in the list

        return True
    else:
        return False
