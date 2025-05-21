from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView, filters
from datetime import datetime, timedelta
from PIL import Image
from PIL import ImageEnhance, ImageOps
from io import BytesIO
from rapidfuzz import process
import pytesseract
import base64
import re
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = 'fyp2025'

# Configure SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'backend' ,'halal_scan.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\misha\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class Ingredient(db.Model):
    __tablename__ = 'ingredients_v2'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ecode = db.Column(db.String(10), nullable=True)
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), nullable=False)
    explanation = db.Column(db.Text)

class Scan(db.Model):
    __tablename__ = 'scans'
    id = db.Column(db.Integer, primary_key=True)
    ingredient_name = db.Column(db.String(100), nullable=False)
    scanned_at = db.Column(db.DateTime, nullable=False)

class EcodeNullFilter(filters.BaseSQLAFilter):
    def __init__(self, column, name):
        super().__init__(column, name, options=(('1', 'Has E-code'), ('0', 'No E-code')))

    def apply(self, query, value, alias=None):
        if value == '1':
            return query.filter(self.column.isnot(None))
        elif value == '0':
            return query.filter(self.column.is_(None))

    def operation(self):
        return 'is'
    
class StatusFilter(filters.BaseSQLAFilter):
    def __init__(self, column, name):
        super().__init__(column, name, options=[
            ('halal', 'Halal'),
            ('doubtful', 'Doubtful'),
            ('haram', 'Haram')
        ])

    def apply(self, query, value, alias=None):
        return query.filter(self.column == value)

    def operation(self):
        return 'is'

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))
    
class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccesible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class IngredientModelView(ModelView):
    column_list = ('name', 'ecode', 'category', 'status', 'explanation')
    form_columns = ('name', 'ecode', 'category', 'status', 'explanation')

    column_filters = [
        filters.FilterEqual(Ingredient.category, 'Category'),
        StatusFilter(Ingredient.status, 'status'),
        EcodeNullFilter(Ingredient.ecode, 'E-code status')
    ]
    column_searchable_list = ['name', 'ecode', 'category', 'status']

def has_ecode(self):
    return bool(self.ecode)

    def on_form_prefill(self, form, id):
        print("Prefill Form: ", form)
        return super().on_form_prefill(form, id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            login_user(user)
            return redirect(url_for('admin.index'))
        else:
            flash('Invalid credentials')
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

class SecureModelView(IngredientModelView):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccesible_callback(self, name, **kwargs):
        return redirect(url_for('login'))
    
admin = Admin(app, name='Admin', template_mode='bootstrap3', index_view=MyAdminIndexView())
admin.add_view(SecureModelView(Ingredient, db.session))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan-camera')
def scan_camera():
    return render_template('camera_scan.html')

@app.route('/scan')
def scan():
    return render_template('scan.html', trigger_upload=True)

@app.route('/ocr', methods=['POST'])
def ocr():
    image = None
    if request.content_type == 'application/json':
        data = request.get_json()
        image_data = data.get('image', '')

        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400

        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            
        except Exception as e:
            return jsonify({'error': 'Invalid base64 image data', 'details': str(e)}), 400

    elif 'file' in request.files:
        file = request.files.get('file')
        try:
            image = Image.open(file.stream)
        except Exception as e:
            return jsonify({'error': 'Failed to read uploaded file', 'details': str(e)}), 400
    else:
        return jsonify({'error': 'Unsupported content type or missing data'}), 400

    image = image.convert('L')  
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    threshold = 128
    image = image.point(lambda x: 0 if x < threshold else 255, '1')  # Binarize
    text = pytesseract.image_to_string(image)
    ingredients = get_ingredients_from_text(text)

    return jsonify({'text': text, 'ingredients': ingredients})

@app.route('/graph')
def graph():
    return render_template('graph.html')

def log_scan(name):
    scan = Scan(ingredient_name=name, scanned_at=datetime.now())
    db.session.add(scan)
    db.session.commit()

def get_ingredients_from_text(text):
    ingredients = []
    seen = set()

    clean_text = text.lower()
    clean_text = re.sub(r'[(){}\[\];:_\-]', ',', clean_text)
    clean_text = re.sub(r'[^a-zA-Z0-9\s,]', '', clean_text)
    clean_text = re.sub(r'[^\w\s,]', '', clean_text)
    clean_text = re.sub(r'\(\s+', '(', clean_text)
    clean_text = re.sub(r'\s+\)', ')', clean_text)
    clean_text = clean_text.replace('(', ',').replace(')', ',')
    tokens = [token.strip() for token in re.split(r'[,|\n]', clean_text) if token.strip()]
    words = re.split(r'[\s\-]+', clean_text)

    known_names = [ingredient.name.lower() for ingredient in Ingredient.query.all() if ingredient.name]

    for phrase in tokens:
        if phrase in seen:
            continue

        match = next((k for k in known_names if k in phrase), None)
        if match:
            ingredient = get_ingredient_details(match)
            if ingredient:
                ingredients.append(ingredient)
                insert_scan(ingredient['name'])
                seen.add(match)
            continue

        fuzzy_result = process.extractOne(phrase, known_names, score_cutoff=85)
        if fuzzy_result:
            match_name, score = fuzzy_result[:2]
            if match_name and match_name not in seen:
                ingredient = get_ingredient_details(match_name)
                if ingredient:
                    ingredients.append(ingredient)
                    insert_scan(ingredient['name'])
                    seen.add(match_name)

    for word in words:
        if word not in seen and len(word) > 2:
            ingredient = get_ingredient_details(word)
            if ingredient:
                ingredients.append(ingredient)
                insert_scan(ingredient['name'])
                seen.add(word)

    ecodes = re.findall(r'\b(?:e|ins)?\s*\d{3,4}\b', text.lower())
    for code in ecodes:
        code_num = re.search(r'\d{3,4}', code).group()
        if code_num not in seen:
            ingredient = get_ingredient_details(code_num)
            if ingredient and ingredient['ecode'] == code_num:
                ingredients.append(ingredient)
                insert_scan(ingredient['name'])
                seen.add(code_num)

    return ingredients

def insert_scan(name):
    scan = Scan(ingredient_name=name, scanned_at=datetime.now())
    db.session.add(scan)
    db.session.commit()

def get_ingredient_details(name):
    ingredient = Ingredient.query.filter_by(ecode=name.strip().lower()).first()
    if ingredient:
        return format_ingredient(ingredient)
    
    ingredient = Ingredient.query.filter(Ingredient.name.ilike(name)).order_by(Ingredient.ecode.isnot(None)).first()
    if ingredient:
        return format_ingredient(ingredient)
    
    return None

def format_ingredient(ingredient):
    return {
        'name': ingredient.name,
        'ecode': ingredient.ecode,
        'category': ingredient.category,
        'status': ingredient.status,
        'explanation': ingredient.explanation,
    }

@app.route('/get-scanned-stats')
def get_scanned_stats():
    period = request.args.get('period', 'weekly')
    if period == 'monthly':
        start_date = datetime.now() - timedelta(days=30)
    else:
        start_date = datetime.now() - timedelta(weeks=1)

    scanned_stats = db.session.query(Scan.ingredient_name, db.func.count(Scan.id).label('total')) \
        .filter(Scan.scanned_at >= start_date) \
        .group_by(Scan.ingredient_name) \
        .order_by(db.func.count(Scan.id).desc()) \
        .limit(10) \
        .all()

    return jsonify([{'ingredient': row[0], 'count': row[1]} for row in scanned_stats])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
