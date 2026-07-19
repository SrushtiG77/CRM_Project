from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='Staff') # Admin or Staff
    
    customers = db.relationship('Customer', backref='staff', lazy=True)

    @property
    def total_sales(self):
        return sum(c.total_spending for c in self.customers)

    @property
    def category_counts(self):
        counts = {'Gold Member': 0, 'Loyal Customer': 0, 'New Customer': 0}
        for c in self.customers:
            if c.category in counts:
                counts[c.category] += 1
            else:
                counts[c.category] = 1
        return counts

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    category = db.Column(db.String(50), default='New Customer') 
    total_spending = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    purchases = db.relationship('Purchase', backref='customer', lazy=True, cascade="all, delete-orphan")
    notes = db.relationship('Note', backref='customer', lazy=True, cascade="all, delete-orphan")

    def update_category(self):
        purchase_count = len(self.purchases)
        if self.total_spending >= 200000 or purchase_count >= 5:
            self.category = 'Gold Member'
        elif self.total_spending >= 50000 or purchase_count >= 3:
            self.category = 'Loyal Customer'
        else:
            self.category = 'New Customer'

class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    purity = db.Column(db.String(20), nullable=False) # e.g. 22K, 24K
    weight = db.Column(db.Float, nullable=False) # grams
    price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
