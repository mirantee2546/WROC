import os
import platform
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Order, TopupRequest
from linebot import LineBotApi
from linebot.models import TextSendMessage

app = Flask(__name__)

# 1. Database Configuration
if platform.system() == 'Windows':
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'wroc_database.db')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/wroc_database.db'

app.config['SECRET_KEY'] = 'dev-key-123'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/slips'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 2. LINE Configuration
LINE_CHANNEL_ACCESS_TOKEN = 'sJqu5ROglXJpMK4l976CaezwEtwB4QS9z/iugKPOJVdx+zQCgEP9+iRP74IfG/NYjQeQw0nTD1bAiGHlUDdyhgtr13u/RHyHkjQRM6brS3lLZ1bN/lSgXk7IKD3jSSwZojoUZ+dZhyOQ8+zRGwCeTgdB04t89/1O/w1cDnyilFU='
LINE_ADMIN_USER_ID = 'Uc96074081e475c7ba28fcb730b80e16e' 
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

def send_line_message(message):
    try:
        line_bot_api.push_message(LINE_ADMIN_USER_ID, TextSendMessage(text=message))
    except Exception as e:
        print(f"Error: {e}")

# 3. DB & Login Manager Init
db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES สำหรับลูกค้า ---

@app.route('/')
@login_required
def index():
    services = [
        {'id': 1, 'name': 'ปั้มไลค์ Facebook', 'price': 0.05},
        {'id': 2, 'name': 'เพิ่มผู้ติดตาม IG', 'price': 0.10}
    ]
    return render_template('index.html', services=services)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash("ชื่อผู้ใช่นี้ถูกใช้ไปแล้ว", "danger")
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # ถ้าเป็น Admin1 ให้กระโดดไปหน้าจัดการระบบ
            if user.username == 'Admin1':
                return redirect(url_for('admin')) 
            return redirect(url_for('index'))
        
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")
    return render_template('login.html')

@app.route('/topup', methods=['GET', 'POST'])
@login_required
def topup():
    if request.method == 'POST':
        amount = request.form.get('amount')
        file = request.files.get('slip')
        if file and amount:
            filename = f"slip_{current_user.id}_{int(time.time())}.jpg"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_request = TopupRequest(user_id=current_user.id, amount=float(amount), slip_image=filename)
            db.session.add(new_request)
            db.session.commit()
            send_line_message(f"💰 เติมเงินใหม่!\n👤: {current_user.username}\n💵: {amount} บาท")
            flash("ส่งหลักฐานแล้ว รอแอดมินอนุมัติครับ", "success")
            return redirect(url_for('index'))
    return render_template('topup.html')

@app.route('/order', methods=['POST'])
@login_required
def place_order():
    quantity = int(request.form.get('quantity'))
    service_id = request.form.get('service')
    link = request.form.get('link')
    price = 0.05 if service_id == '1' else 0.10
    total = quantity * price
    if current_user.balance < total:
        return "ยอดเงินไม่พอ"
    current_user.balance -= total
    new_order = Order(user_id=current_user.id, service_name="ID: "+service_id, url_link=link, quantity=quantity, total_price=total)
    db.session.add(new_order)
    db.session.commit()
    send_line_message(f"🔔 ออเดอร์ใหม่!\n👤: {current_user.username}\n🔗: {link}")
    return redirect(url_for('view_history'))

@app.route('/history')
@login_required
def view_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('history.html', orders=orders)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ROUTES สำหรับ ADMIN ---

@app.route('/admin') # ลิงก์เข้าคือ /admin
@login_required
def admin():
    if current_user.username != 'Admin1':
        return redirect(url_for('login'))
    all_orders = Order.query.order_by(Order.id.desc()).all()
    topup_requests = TopupRequest.query.filter_by(status='Pending').all()
    return render_template('admin.html', orders=all_orders, topups=topup_requests)

@app.route('/admin/approve/<int:id>')
@login_required
def approve_topup(id):
    if current_user.username != 'Admin1': return "Unauthorized", 403
    top_req = TopupRequest.query.get(id)
    if top_req and top_req.status == 'Pending':
        target_user = User.query.get(top_req.user_id)
        target_user.balance += top_req.amount
        top_req.status = 'Approved'
        db.session.commit()
        flash("อนุมัติสำเร็จ", "success")
    return redirect(url_for('admin'))

@app.route('/update_status/<int:order_id>/<string:new_status>')
@login_required
def update_status(order_id, new_status):
    if current_user.username != 'Admin1': return "Unauthorized", 403
    order = Order.query.get(order_id)
    if order:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/refund/<int:order_id>')
@login_required
def refund_order(order_id):
    if current_user.username != 'Admin1': return "Unauthorized", 403
    order = Order.query.get(order_id)
    if order and order.status != 'Canceled':
        target_user = User.query.get(order.user_id)
        target_user.balance += order.total_price
        order.status = 'Canceled'
        db.session.commit()
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10000)