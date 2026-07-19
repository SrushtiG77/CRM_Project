from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, Customer, Purchase, Note
import os
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gold_crm_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CLI to initialize DB and Admin ---
@app.cli.command("initdb")
def initdb():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            new_admin = User(username='admin', password=hashed_pw, role='Admin')
            db.session.add(new_admin)
            db.session.commit()
            print("Database initialized and 'admin' user created (password: admin123).")
        else:
            print("Database already initialized.")

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw, role='Staff')
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_customers = Customer.query.count()
    loyal_customers = Customer.query.filter_by(category='Loyal Customer').count()
    gold_members = Customer.query.filter_by(category='Gold Member').count()
    
    total_revenue_result = db.session.query(func.sum(Purchase.price)).scalar()
    total_revenue = total_revenue_result if total_revenue_result else 0.0
    
    # Top 5 customers
    top_customers = Customer.query.order_by(Customer.total_spending.desc()).limit(5).all()

    return render_template('dashboard.html', 
                           total_customers=total_customers,
                           loyal_customers=loyal_customers, 
                           gold_members=gold_members,
                           total_revenue=total_revenue,
                           top_customers=top_customers)

@app.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    search = request.args.get('search')
    if search:
        customers = Customer.query.filter((Customer.name.contains(search)) | (Customer.phone.contains(search))).all()
    else:
        customers = Customer.query.all()
        
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        email = request.form.get('email')
        total_spending = request.form.get('total_spending')
        total_spending = float(total_spending) if total_spending else 0.0
        
        # Primary key logic: prevent duplicate customers
        existing_customer = Customer.query.filter((Customer.name == name) | (Customer.phone == phone)).first()
        if existing_customer:
            flash('Error: A customer with this Name or Phone already exists!', 'danger')
            return redirect(url_for('customers'))
        
        new_customer = Customer(name=name, phone=phone, address=address, email=email, total_spending=total_spending, staff_id=current_user.id)
        # Ensure category is logically set
        new_customer.update_category()

        db.session.add(new_customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
        
    staff_members = User.query.all()
    return render_template('customers.html', customers=customers, search_query=search, staff_members=staff_members)

@app.route('/customer/<int:id>/edit', methods=['POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    customer.name = request.form.get('name')
    customer.phone = request.form.get('phone')
    customer.address = request.form.get('address')
    customer.email = request.form.get('email')
    db.session.commit()
    flash('Customer updated successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/customer/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/customer/<int:id>/purchase', methods=['POST'])
@login_required
def add_purchase(id):
    customer = Customer.query.get_or_404(id)
    product_name = request.form.get('product_name')
    purity = request.form.get('purity')
    weight = float(request.form.get('weight'))
    price = float(request.form.get('price'))
    
    new_purchase = Purchase(customer_id=customer.id, product_name=product_name, 
                            purity=purity, weight=weight, price=price)
    
    # Update customer spending
    customer.total_spending += price
    customer.update_category()
    
    db.session.add(new_purchase)
    db.session.commit()
    flash('Purchase added successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/customer/<int:id>/note', methods=['POST'])
@login_required
def add_note(id):
    customer = Customer.query.get_or_404(id)
    content = request.form.get('content')
    
    new_note = Note(customer_id=customer.id, content=content)
    db.session.add(new_note)
    db.session.commit()
    flash('Note added successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/staff')
@login_required
def staff():
    all_staff = User.query.all()
    return render_template('staff.html', staff_members=all_staff)

@app.route('/api/gold_rate')
@login_required
def api_gold_rate():
    try:
        import urllib.request, json
        # Fetch USD per Troy Ounce (Spot Gold)
        req_gold = urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/GC=F', headers={'User-Agent': 'Mozilla/5.0'})
        res_gold = urllib.request.urlopen(req_gold).read().decode('utf-8')
        gold_usd_per_oz = json.loads(res_gold)['chart']['result'][0]['meta']['regularMarketPrice']
        
        # Fetch USD to INR exchange rate
        req_inr = urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/INR=X', headers={'User-Agent': 'Mozilla/5.0'})
        res_inr = urllib.request.urlopen(req_inr).read().decode('utf-8')
        usd_inr_rate = json.loads(res_inr)['chart']['result'][0]['meta']['regularMarketPrice']
        
        # 1 Troy Ounce = 31.1034768 grams. 
        # Prices are roughly wholesale, we add a conservative 3% estimated premium for markup/making standard
        premium = 1.03
        gold_price_inr_per_gram_24k = ((gold_usd_per_oz * usd_inr_rate) / 31.1034768) * premium
        
        # Define Silver rate statically or approximation as Yahoo silver is SI=F (not strictly req but good for future)
        req_silver = urllib.request.Request('https://query1.finance.yahoo.com/v8/finance/chart/SI=F', headers={'User-Agent': 'Mozilla/5.0'})
        try:
            res_silver = urllib.request.urlopen(req_silver).read().decode('utf-8')
            silver_usd_per_oz = json.loads(res_silver)['chart']['result'][0]['meta']['regularMarketPrice']
            silver_inr_per_gram = ((silver_usd_per_oz * usd_inr_rate) / 31.1034768) * premium
        except:
            silver_inr_per_gram = 85.0 # Fallback
        
        return jsonify({
            'status': 'success',
            'rates': {
                '24K': round(gold_price_inr_per_gram_24k, 2),
                '22K': round(gold_price_inr_per_gram_24k * (22/24), 2),
                '18K': round(gold_price_inr_per_gram_24k * (18/24), 2),
                'Silver': round(silver_inr_per_gram, 2)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/customer/<int:id>')
@login_required
def api_customer(id):
    customer = Customer.query.get_or_404(id)
    purchases = [{'id': p.id, 'product_name': p.product_name, 'purity': p.purity, 
                  'weight': p.weight, 'price': p.price, 'date': p.purchase_date.strftime('%Y-%m-%d')} 
                 for p in customer.purchases]
    notes = [{'id': n.id, 'content': n.content, 'date': n.date_added.strftime('%Y-%m-%d')} for n in customer.notes]
    
    customer_data = {
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone,
        'address': customer.address,
        'email': customer.email,
        'category': customer.category,
        'total_spending': customer.total_spending,
        'created_at': customer.created_at.strftime('%Y-%m-%d'),
        'staff_id': customer.staff_id,
        'staff_name': customer.staff.username if customer.staff else 'Unassigned',
        'purchases': purchases,
        'notes': notes
    }
    return jsonify(customer_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Initialize admin on first run if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            new_admin = User(username='admin', password=hashed_pw, role='Admin')
            db.session.add(new_admin)
            db.session.commit()
            print("Database initialized and 'admin' user created (password: admin123).")
    app.run(debug=True, port=5000)
