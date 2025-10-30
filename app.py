import Backend
import DB.DB_Back as db
from Websocket_Server import init_websocket_server

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify



app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with a secure key


# Initialize WebSocket server
init_websocket_server()

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
            return render_template('index.html', products=products, Thumbnails=Thumbnails, IDs=IDs, projects=projects)


        else:
            flash('Invalid username or password!', 'error')
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

if __name__ == '__main__':
    app.run(debug=True)