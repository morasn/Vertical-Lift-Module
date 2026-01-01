import os
import Backend
import DB.DB_Back as db
from Websocket_Server import init_websocket_server, WS_Send_sync
import Websocket_Server as WSS

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
import json


app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with a secure key


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
    
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    products, Thumbnails, IDs = Backend.Unique_Product_Families_Get()
    projects = db.Get_Unique_Projects()
    return render_template('index.html', products=products, Thumbnails=Thumbnails, IDs=IDs, projects=projects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if Backend.First_Operator_Check():
        flash('No operators found. Please create the first operator account.', 'info')
        return redirect(url_for('create_first_operator'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        [result, Name, AccessLevel] = Backend.LogIn_Check(username, password)
        if result is True:
            session['username'] = username
            session['Name'] = Name
            session['Access_Level'] = AccessLevel
            products, Thumbnails, IDs = Backend.Unique_Product_Families_Get()
            projects = db.Get_Unique_Projects()

            db.log_event("INFO", f"User {username} logged in", "Server", transaction_type="USER_LOGIN")

            return render_template('index.html', products=products, Thumbnails=Thumbnails, IDs=IDs, projects=projects)


        else:
            flash('Invalid username or password!', 'error')
            db.log_event("WARNING", f"Failed login attempt for user {username}", "Server", transaction_type="USER_LOGIN_FAILED")
    return render_template('login.html')

@app.route('/create_first_operator', methods=['GET', 'POST'])
def create_first_operator():
    if not Backend.First_Operator_Check():
        return redirect(url_for('login'))
    if request.method == 'POST':
        id = request.form['work_id']
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        access_level = 4  # Super Admin by default as its the first account
        result = db.Operator_Add(id, name, username, password, access_level)
        if result is True:
            flash('First operator account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Error creating operator: {result}', 'error')
    return render_template('create_first_operator.html')

@app.route('/logout')
def logout():
    db.log_event("INFO", f"User {session.get('username')} logged out", "Server", transaction_type="USER_LOGOUT")
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/view_shelves')
def view_shelves():
    if 'username' not in session:
        return redirect(url_for('login'))
    # shelves = db.Get_All_Shelves()
    return render_template('view_shelves.html')

@app.route('/manage_users')
def manage_users():
    if 'username' not in session or session['Access_Level'] <= 2:
        return redirect(url_for('login'))
    # users = db.Get_All_Operators()
    return render_template('manage_users.html')


@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        product_id = request.form['product_id']
        name = request.form['name']
        description = request.form['description']
        family_name = request.form['family_name']
        family_item = request.form['family_item']
        weight = float(request.form['weight'])
        rop = int(request.form['rop'])
        oh = int(request.form['oh'])
        length = float(request.form['length'])
        width = float(request.form['width'])
        height = float(request.form['height'])
        tags = request.form['tags'].split(',') if request.form['tags'] else []
        projects = request.form.getlist('projects') if request.form.getlist('projects') else []
        Thumbnail = request.files.get('thumb')
        photos = request.files.getlist('photos')

        result = Backend.Add_Product(product_id, name, description, family_name, family_item, weight, rop, oh, length, width, height, tags, projects, Thumbnail, photos)
        if result is True:
            flash('Product added successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash(f'Error adding product: {result}', 'error')
            return redirect(url_for('add_product'))
    return render_template('add_product.html')

@app.route('/add_shelf', methods=['GET', 'POST'])
def add_shelf():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        from shared_states import shelf_properties
        
        shelf_id = request.form['shelf_id']
        position = request.form['position']
        RacksAvailable = int(request.form.get('racks_available', 1))
        
        if position[0] not in ['F', 'B'] or not (int(position[1:]) > shelf_properties['min_level'] and int(position[1:]) < shelf_properties['max_level']):
            flash(f'Invalid shelf position: {position}', 'error')
            return redirect(url_for('add_shelf'))

        result = db.Shelves_DB_Add(shelf_id, position, RacksAvailable=RacksAvailable)
        if result is True:
            flash('Shelf added successfully!', 'success')
        else:
            flash(f'Error adding shelf: {result}', 'error')
        return redirect(url_for('add_shelf'))
    return render_template('add_shelf.html')


@app.route('/product/<product_id>', methods=['GET'])
def product_page(product_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    result = Backend.Product_Read(product_id)
    if isinstance(result, str):
        flash(result, 'error')
        return redirect(url_for('index'))
    product, family, projects = result
    images = Backend.Get_Product_Images(product_id)
    return render_template('product.html', product=product, family=family, projects=projects, images=images)


@app.route('/project/<project>', methods=['GET'])
def project_page(project):
    if 'username' not in session:
        return redirect(url_for('login'))
    products = Backend.Products_Project_Search(project)
    if isinstance(products, str):
        flash(products, 'error')
        return redirect(url_for('index'))
    return render_template('project.html', products=products, project=project)

@app.route('/api/family_names', methods=['GET'])
def get_family_names():
    family_names = db.Products_Family_Search(request.args.get('q', ''))
    return jsonify(family_names)

@app.route('/api/projects', methods=['GET'])
def get_projects():
    family_names = db.Products_Projects_Search(request.args.get('q', ''))
    return jsonify(family_names)



@app.route('/api/product_interaction/<product_id>/<operation>', methods=['GET'])
def Product_Interaction(product_id, operation):
    operator = session.get('username') # Get operator from session or default to 'unknown'

    Backend.Website_Transaction([product_id],operation,operator )
    flash(f'Product {operation} request for {product_id} has been processed.', 'success')
    return redirect(url_for('product_page', product_id=product_id))

@app.route('/api/project_dispense/<project_id>/', methods=['GET'])
def Project_Dispense(project_id):

    product_ids = request.args.getlist('product_id')
    
    operation = 'dispense' # By default is dispense as it is for project
    operator = session.get('username') # Get operator from session or default to 'unknown'

    Backend.Website_Transaction(product_ids,operation,operator, project=project_id)
    flash(f'Project {operation} request for {project_id} has been processed.', 'success')
    return redirect(url_for('project_page', project=project_id))

@app.route('/api/product_inventory/<product_id>', methods=['GET'])
def product_inventory(product_id):
    if 'username' not in session or session['Access_Level'] <= 1:
        return jsonify({'error': 'Unauthorized access'}), 403

    inventory_data = Backend.Get_Product_Inventory(product_id)
    if isinstance(inventory_data, str):
        return jsonify({'error': inventory_data}), 400

    return jsonify(inventory_data)


@app.route('/config_vlm')
def config_vlm():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('config_VLM.html')


@app.route('/machine_logs')
def machine_logs():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('machine_logs.html')


@app.route('/api/logs', methods=['GET'])
def api_logs():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    # parse filters
    level = request.args.get('level')
    source = request.args.get('source')
    transaction_type = request.args.get('transaction_type')
    transaction_id = request.args.get('transaction_id')
    q = request.args.get('q')
    start = request.args.get('start')
    end = request.args.get('end')
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except Exception:
        limit = 50
        offset = 0

    logs, total = Backend.Get_Logs(level=level, source=source, transaction_type=transaction_type, transaction_id=transaction_id, q=q, start=start, end=end, limit=limit, offset=offset)
    return jsonify({'logs': logs, 'total': total})


@app.route('/api/log_selectors', methods=['GET'])
def api_log_selectors():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    selectors = Backend.Get_Log_Selectors()
    return jsonify(selectors)


@app.route('/api/vlm_config', methods=['GET'])
def get_vlm_config():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    # Fetch current config using DB layer
    config = db.VLM_Get_Configuration()
    if not config:
        return jsonify({'error': 'No config found'}), 404
    return jsonify(config)



@app.route('/api/vlm_config', methods=['POST'])
def update_vlm_config():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400
    required_fields = [
        'Normal_Speed', 'Approach_Speed', 'Stop_Pulse',
        'For_Pulse', 'Back_Pulse', 'Collect_Time', 'Return_Time', 'hall_N_thresh', 'hall_S_thresh'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing fields'}), 400
    # Convert and validate numeric values
    try:
        cfg = {
            'Normal_Speed': int(data['Normal_Speed']),
            'Approach_Speed': int(data['Approach_Speed']),
            'Steps_Per_Floor': int(data['Steps_Per_Floor']),
            'Stop_Pulse': int(data['Stop_Pulse']),
            'For_Pulse': int(data['For_Pulse']),
            'Back_Pulse': int(data['Back_Pulse']),
            'Collect_Time': int(data['Collect_Time']),
            'Return_Time': int(data['Return_Time']),
            'hall_N_thresh': int(data['hall_N_thresh']),
            'hall_S_thresh': int(data['hall_S_thresh']),
        }
    except Exception as e:
        return jsonify({'error': f'Invalid numeric values: {e}'}), 400

    # Update DB
    res = db.VLM_Update_Configuration(
        cfg['Normal_Speed'],
        cfg['Approach_Speed'],
        cfg['Steps_Per_Floor'],
        cfg['Stop_Pulse'],
        cfg['For_Pulse'],
        cfg['Back_Pulse'],
        cfg['Collect_Time'],
        cfg['Return_Time'],
        cfg['hall_N_thresh'],
        cfg['hall_S_thresh'],
    )
    if isinstance(res, Exception):
        db.log_event('ERROR', f'VLM config update failed: {res}', "Server", transaction_type='VLM_CONFIG_UPDATE')
        return jsonify({'error': 'DB update failed'}), 500

    # Send to ESP32 using standard message format (code 501)
    payload = {'code': 501}
    payload.update(cfg)
    WS_Send_sync(json.dumps(payload))
    db.log_event('INFO', 'VLM configuration updated via web.', transaction_type='VLM_CONFIG_UPDATE')
    return jsonify({'status': 'success', 'message': 'VLM config updated and sent to ESP32.'})


@app.route('/api/vlm_vertical', methods=['POST'])
def vlm_vertical():
    """Fire-and-forget vertical motor motion (code 600). Accepts JSON: { steps: int, direction?: int }"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    data = request.get_json() or {}
    if 'steps' not in data:
        return jsonify({'error': 'Missing steps field'}), 400
    try:
        steps = int(data['steps'])
    except Exception as e:
        return jsonify({'error': f'Invalid steps: {e}'}), 400
    direction = data.get('direction')
    if direction is not None:
        if not isinstance(direction, bool):
            return jsonify({'error': 'Invalid direction'}), 400

    tid = db.Transaction_ID_Generator()
    payload = {'code': 600, 'steps': steps, 'transaction_id': tid}
    if direction is not None:
        payload['direction'] = direction

    WS_Send_sync(json.dumps(payload))
    db.log_event('INFO', f'Vertical motion queued: steps={steps} direction={direction}', "Server",transaction_type='VLM_MANUAL_VERTICAL', transaction_id=tid)
    return jsonify({'status': 'sent', 'transaction_id': tid})


@app.route('/api/vlm_horizontal', methods=['POST'])
def vlm_horizontal():
    """Fire-and-forget horizontal motion (code 601). Accepts JSON: { duration_sec: float, left_pwm: int, right_pwm: int }"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    data = request.get_json() or {}
    if 'duration_sec' not in data or 'left_pwm' not in data or 'right_pwm' not in data:
        return jsonify({'error': 'Missing duration_sec, left_pwm, or right_pwm'}), 400
    try:
        duration_sec = float(data['duration_sec'])
        left_pwm = int(data['left_pwm'])
        right_pwm = int(data['right_pwm'])
        duration_ms = int(duration_sec * 1000)  # Convert to milliseconds
    except Exception as e:
        return jsonify({'error': f'Invalid numeric values: {e}'}), 400

    tid = db.Transaction_ID_Generator()
    payload = {'code': 601, 'duration_ms': duration_ms, 'left_pwm_freq': left_pwm, 'right_pwm_freq': right_pwm, 'transaction_id': tid}
    WS_Send_sync(json.dumps(payload))
    db.log_event('INFO', f'Horizontal motion queued: duration={duration_sec}s ({duration_ms}ms) left_pwm={left_pwm} right_pwm={right_pwm}', "Server", transaction_type='VLM_MANUAL_HORIZONTAL', transaction_id=tid)
    return jsonify({'status': 'sent', 'transaction_id': tid})


@app.route('/api/vlm_hall_immediate', methods=['GET'])
def vlm_hall_immediate():
    """Fire-and-forget immediate hall sensor request (code 602)."""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized access'}), 403
    tid = db.Transaction_ID_Generator()
    payload = {'code': 602, 'transaction_id': tid}
    WS_Send_sync(json.dumps(payload))
    db.log_event('INFO', 'Immediate hall sensor read requested',"Server" ,transaction_type='VLM_HALL_READ', transaction_id=tid)
    return jsonify({'status': 'sent', 'transaction_id': tid})


@app.route('/debug/ws_status', methods=['GET'])
def debug_ws_status():
    """Return WebSocket connection status and queue size for debugging."""
    connected = False
    try:
        connected = bool(getattr(WSS, 'ws', None) and getattr(WSS.ws, 'open', False))
    except Exception:
        connected = False
    qsize = None
    try:
        qsize = WSS.message_queue.qsize()
    except Exception:
        qsize = None
    return jsonify({'connected': connected, 'queue_size': qsize})


if __name__ == '__main__':
    # Only start WebSocket server in the reloader child (when WERKZEUG_RUN_MAIN is set)
    # This ensures Flask and WebSocket share the same process/memory space
    is_reloader_child = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    print(f"[app.py] Starting (WERKZEUG_RUN_MAIN={os.environ.get('WERKZEUG_RUN_MAIN')}, is_child={is_reloader_child})")
    if is_reloader_child:
        print("[app.py] Reloader child: starting WebSocket server")
        init_websocket_server()
    else:
        print("[app.py] Reloader parent: skipping WebSocket server")
    app.run(host='0.0.0.0', port=5000, debug=True)