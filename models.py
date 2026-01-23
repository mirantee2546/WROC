from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ตารางผู้ใช้งาน
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, default=0.0)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ตารางการสั่งซื้อบริการ
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_name = db.Column(db.String(100))
    url_link = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Float)
    status = db.Column(db.String(20), default='Pending')

# ตารางแจ้งเติมเงินและแนบสลิป
class TopupRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    slip_image = db.Column(db.String(100), nullable=False) # เก็บชื่อไฟล์รูปภาพสลิป
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    timestamp = db.Column(db.DateTime, default=db.func.now())