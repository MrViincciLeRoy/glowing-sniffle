"""
ERPNext Mock API Server with SQL Database Storage
Mimics ERPNext API endpoints and persists data to a remote SQL database
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool

app = Flask(__name__)

# Database Configuration
# Set your database URL as an environment variable or directly here
# Format: postgresql://user:password@host:port/database
# or: mysql+pymysql://user:password@host:port/database
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@host:port/dbname')

# SQLAlchemy setup
Base = declarative_base()

# Database Models
class Document(Base):
    """Generic document storage table"""
    __tablename__ = 'erpnext_documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doctype = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    data = Column(Text, nullable=False)  # JSON string
    docstatus = Column(Integer, default=0)
    creation = Column(DateTime, default=datetime.utcnow)
    modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = Column(String(100), default='Administrator')


class Counter(Base):
    """Counter for generating document names"""
    __tablename__ = 'erpnext_counters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    doctype = Column(String(100), nullable=False, unique=True)
    counter = Column(Integer, default=1)


# Initialize database
try:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,  # Disable connection pooling for serverless
        echo=False
    )
    Base.metadata.create_all(engine)
    SessionLocal = scoped_session(sessionmaker(bind=engine))
    print("✅ Database connected successfully")
except Exception as e:
    print(f"❌ Database connection failed: {str(e)}")
    print("   Falling back to in-memory storage")
    engine = None
    SessionLocal = None


# Fallback in-memory storage
documents_memory = {
    'Customer': {},
    'Journal Entry': {},
    'Purchase Invoice': {},
    'Payment Entry': {}
}
counters_memory = {
    'Customer': 1,
    'Journal Entry': 1,
    'Purchase Invoice': 1,
    'Payment Entry': 1
}


# Mock authentication
VALID_API_KEYS = {
    'test_api_key': 'test_api_secret',
    'demo_key': 'demo_secret'
}


def get_db():
    """Get database session"""
    if SessionLocal:
        return SessionLocal()
    return None


def authenticate():
    """Check if request has valid authentication"""
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('token '):
        token = auth_header[6:]
        try:
            api_key, api_secret = token.split(':')
            if VALID_API_KEYS.get(api_key) == api_secret:
                return True
        except:
            pass
    
    return False


def get_next_counter(doctype, db=None):
    """Get and increment counter for document name generation"""
    if db:
        counter_obj = db.query(Counter).filter_by(doctype=doctype).first()
        if not counter_obj:
            counter_obj = Counter(doctype=doctype, counter=1)
            db.add(counter_obj)
            db.commit()
        
        current = counter_obj.counter
        counter_obj.counter += 1
        db.commit()
        return current
    else:
        # Fallback to memory
        current = counters_memory.get(doctype, 1)
        counters_memory[doctype] = current + 1
        return current


def generate_doc_name(doctype, db=None):
    """Generate a document name like ERPNext does"""
    counter = get_next_counter(doctype, db)
    
    if doctype == 'Customer':
        return f"CUST-{counter:05d}"
    elif doctype == 'Journal Entry':
        return f"ACC-JV-{datetime.now().year}-{counter:05d}"
    elif doctype == 'Purchase Invoice':
        return f"ACC-PINV-{datetime.now().year}-{counter:05d}"
    elif doctype == 'Payment Entry':
        return f"ACC-PAY-{datetime.now().year}-{counter:05d}"
    
    return f"{doctype}-{counter}"


def save_document(doctype, doc_name, doc_data, db=None):
    """Save document to database or memory"""
    if db:
        # Check if document exists
        existing = db.query(Document).filter_by(name=doc_name).first()
        
        if existing:
            existing.data = json.dumps(doc_data)
            existing.modified = datetime.utcnow()
            existing.docstatus = doc_data.get('docstatus', 0)
        else:
            doc = Document(
                doctype=doctype,
                name=doc_name,
                data=json.dumps(doc_data),
                docstatus=doc_data.get('docstatus', 0),
                owner=doc_data.get('owner', 'Administrator')
            )
            db.add(doc)
        
        db.commit()
    else:
        # Fallback to memory
        if doctype not in documents_memory:
            documents_memory[doctype] = {}
        documents_memory[doctype][doc_name] = doc_data


def get_document(doctype, doc_name, db=None):
    """Get document from database or memory"""
    if db:
        doc = db.query(Document).filter_by(doctype=doctype, name=doc_name).first()
        if doc:
            return json.loads(doc.data)
        return None
    else:
        # Fallback to memory
        return documents_memory.get(doctype, {}).get(doc_name)


def list_documents(doctype, limit_start=0, limit_page_length=20, db=None):
    """List documents from database or memory"""
    if db:
        docs = db.query(Document).filter_by(doctype=doctype)\
            .offset(limit_start)\
            .limit(limit_page_length)\
            .all()
        return [json.loads(doc.data) for doc in docs]
    else:
        # Fallback to memory
        doc_list = list(documents_memory.get(doctype, {}).values())
        return doc_list[limit_start:limit_start + limit_page_length]


def delete_document(doctype, doc_name, db=None):
    """Delete document from database or memory"""
    if db:
        doc = db.query(Document).filter_by(doctype=doctype, name=doc_name).first()
        if doc:
            db.delete(doc)
            db.commit()
            return True
        return False
    else:
        # Fallback to memory
        if doctype in documents_memory and doc_name in documents_memory[doctype]:
            del documents_memory[doctype][doc_name]
            return True
        return False


@app.route('/api/method/frappe.auth.get_logged_user', methods=['GET'])
def get_logged_user():
    """Test endpoint to verify authentication"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    return jsonify({
        'message': 'Administrator'
    })


@app.route('/api/resource/<doctype>', methods=['GET'])
def get_resources(doctype):
    """GET /api/resource/{doctype} - List resources"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    db = get_db()
    
    try:
        limit_start = int(request.args.get('limit_start', 0))
        limit_page_length = int(request.args.get('limit_page_length', 20))
        
        doc_list = list_documents(doctype, limit_start, limit_page_length, db)
        
        return jsonify({
            'data': doc_list
        })
    finally:
        if db:
            db.close()


@app.route('/api/resource/<doctype>/<name>', methods=['GET'])
def get_resource(doctype, name):
    """GET /api/resource/{doctype}/{name} - Get single resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    db = get_db()
    
    try:
        doc = get_document(doctype, name, db)
        
        if not doc:
            return jsonify({
                'exc': f'{doctype} {name} not found',
                'exc_type': 'DoesNotExistError'
            }), 404
        
        return jsonify({
            'data': doc
        })
    finally:
        if db:
            db.close()


@app.route('/api/resource/Customer', methods=['POST'])
def create_customer():
    """POST /api/resource/Customer - Create customer"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    if not data.get('customer_name'):
        return jsonify({
            'exc': 'Mandatory field customer_name missing',
            'exc_type': 'ValidationError'
        }), 400
    
    db = get_db()
    
    try:
        doc_name = generate_doc_name('Customer', db)
        
        customer = {
            'name': doc_name,
            'doctype': 'Customer',
            'customer_name': data.get('customer_name'),
            'customer_type': data.get('customer_type', 'Company'),
            'customer_group': data.get('customer_group', 'All Customer Groups'),
            'territory': data.get('territory', 'All Territories'),
            'email_id': data.get('email_id'),
            'mobile_no': data.get('mobile_no'),
            'creation': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'owner': 'Administrator',
            'docstatus': 0
        }
        
        save_document('Customer', doc_name, customer, db)
        
        return jsonify({
            'data': customer
        }), 201
    finally:
        if db:
            db.close()


@app.route('/api/resource/Journal Entry', methods=['POST'])
def create_journal_entry():
    """POST /api/resource/Journal Entry - Create journal entry"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    if not data.get('company'):
        return jsonify({
            'exc': 'Mandatory field company missing',
            'exc_type': 'ValidationError'
        }), 400
    
    if not data.get('accounts') or len(data['accounts']) < 2:
        return jsonify({
            'exc': 'At least 2 accounts required for a Journal Entry',
            'exc_type': 'ValidationError'
        }), 400
    
    total_debit = sum(acc.get('debit_in_account_currency', 0) for acc in data['accounts'])
    total_credit = sum(acc.get('credit_in_account_currency', 0) for acc in data['accounts'])
    
    if abs(total_debit - total_credit) > 0.01:
        return jsonify({
            'exc': f'Debit ({total_debit}) must equal Credit ({total_credit})',
            'exc_type': 'ValidationError'
        }), 400
    
    db = get_db()
    
    try:
        doc_name = generate_doc_name('Journal Entry', db)
        
        journal_entry = {
            'name': doc_name,
            'doctype': 'Journal Entry',
            'company': data.get('company'),
            'posting_date': data.get('posting_date', datetime.now().strftime('%Y-%m-%d')),
            'voucher_type': data.get('voucher_type', 'Journal Entry'),
            'accounts': data.get('accounts'),
            'user_remark': data.get('user_remark', ''),
            'reference_number': data.get('reference_number', ''),
            'total_debit': total_debit,
            'total_credit': total_credit,
            'difference': 0,
            'creation': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'owner': 'Administrator',
            'docstatus': 0
        }
        
        save_document('Journal Entry', doc_name, journal_entry, db)
        
        return jsonify({
            'data': journal_entry
        }), 201
    finally:
        if db:
            db.close()


@app.route('/api/resource/Purchase Invoice', methods=['POST'])
def create_purchase_invoice():
    """POST /api/resource/Purchase Invoice - Create purchase invoice"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    if not data.get('supplier'):
        return jsonify({
            'exc': 'Mandatory field supplier missing',
            'exc_type': 'ValidationError'
        }), 400
    
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({
            'exc': 'At least 1 item required for Purchase Invoice',
            'exc_type': 'ValidationError'
        }), 400
    
    db = get_db()
    
    try:
        doc_name = generate_doc_name('Purchase Invoice', db)
        total = sum(item.get('amount', 0) for item in data['items'])
        
        purchase_invoice = {
            'name': doc_name,
            'doctype': 'Purchase Invoice',
            'supplier': data.get('supplier'),
            'company': data.get('company'),
            'posting_date': data.get('posting_date', datetime.now().strftime('%Y-%m-%d')),
            'items': data.get('items'),
            'total': total,
            'grand_total': total,
            'outstanding_amount': total,
            'status': 'Draft',
            'creation': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'owner': 'Administrator',
            'docstatus': 0
        }
        
        save_document('Purchase Invoice', doc_name, purchase_invoice, db)
        
        return jsonify({
            'data': purchase_invoice
        }), 201
    finally:
        if db:
            db.close()


@app.route('/api/resource/Payment Entry', methods=['POST'])
def create_payment_entry():
    """POST /api/resource/Payment Entry - Create payment entry"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    if not data.get('payment_type'):
        return jsonify({
            'exc': 'Mandatory field payment_type missing',
            'exc_type': 'ValidationError'
        }), 400
    
    if not data.get('party_type') or not data.get('party'):
        return jsonify({
            'exc': 'Mandatory fields party_type and party missing',
            'exc_type': 'ValidationError'
        }), 400
    
    db = get_db()
    
    try:
        doc_name = generate_doc_name('Payment Entry', db)
        
        payment_entry = {
            'name': doc_name,
            'doctype': 'Payment Entry',
            'payment_type': data.get('payment_type'),
            'party_type': data.get('party_type'),
            'party': data.get('party'),
            'company': data.get('company'),
            'posting_date': data.get('posting_date', datetime.now().strftime('%Y-%m-%d')),
            'paid_amount': data.get('paid_amount', 0),
            'received_amount': data.get('received_amount', 0),
            'paid_from': data.get('paid_from', ''),
            'paid_to': data.get('paid_to', ''),
            'reference_no': data.get('reference_no', ''),
            'reference_date': data.get('reference_date', datetime.now().strftime('%Y-%m-%d')),
            'status': 'Draft',
            'creation': datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'owner': 'Administrator',
            'docstatus': 0
        }
        
        save_document('Payment Entry', doc_name, payment_entry, db)
        
        return jsonify({
            'data': payment_entry
        }), 201
    finally:
        if db:
            db.close()


@app.route('/api/resource/<doctype>/<name>', methods=['PUT'])
def update_resource(doctype, name):
    """PUT /api/resource/{doctype}/{name} - Update resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    db = get_db()
    
    try:
        doc = get_document(doctype, name, db)
        
        if not doc:
            return jsonify({
                'exc': f'{doctype} {name} not found',
                'exc_type': 'DoesNotExistError'
            }), 404
        
        update_data = request.get_json()
        doc.update(update_data)
        doc['modified'] = datetime.now().isoformat()
        
        save_document(doctype, name, doc, db)
        
        return jsonify({
            'data': doc
        })
    finally:
        if db:
            db.close()


@app.route('/api/resource/<doctype>/<name>', methods=['DELETE'])
def delete_resource(doctype, name):
    """DELETE /api/resource/{doctype}/{name} - Delete resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    db = get_db()
    
    try:
        success = delete_document(doctype, name, db)
        
        if not success:
            return jsonify({
                'exc': f'{doctype} {name} not found',
                'exc_type': 'DoesNotExistError'
            }), 404
        
        return jsonify({
            'message': 'ok'
        })
    finally:
        if db:
            db.close()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    db = get_db()
    db_status = "connected" if db else "in-memory fallback"
    
    if db:
        try:
            count = db.query(Document).count()
            db.close()
            doc_count = count
        except:
            doc_count = 0
    else:
        doc_count = sum(len(docs) for docs in documents_memory.values())
    
    return jsonify({
        'status': 'ok',
        'message': 'ERPNext Mock API is running',
        'database': db_status,
        'total_documents': doc_count
    })


@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'exc': 'Not Found',
        'exc_type': 'NotFoundError'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'exc': str(e),
        'exc_type': 'InternalError'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ERPNext Mock API Server with SQL Database")
    print("=" * 60)
    print("\nDatabase:")
    print(f"  Status: {'✅ Connected' if engine else '❌ Using in-memory fallback'}")
    if engine:
        print(f"  URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'configured'}")
    print("\nAuthentication:")
    print("  API Key: test_api_key")
    print("  API Secret: test_api_secret")
    print("  Header: Authorization: token test_api_key:test_api_secret")
    print("\nStarting server on http://localhost:8000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8000, debug=True)
