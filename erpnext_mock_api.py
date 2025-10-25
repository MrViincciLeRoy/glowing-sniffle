"""
ERPNext Mock API Server
Mimics ERPNext API endpoints for testing the erpnext_connector module
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import re

app = Flask(__name__)

# In-memory storage for created documents
documents = {
    'Customer': {},
    'Journal Entry': {},
    'Purchase Invoice': {},
    'Payment Entry': {}
}

# Counter for generating unique document names
counters = {
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


def authenticate():
    """Check if request has valid authentication"""
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('token '):
        token = auth_header[6:]  # Remove 'token ' prefix
        try:
            api_key, api_secret = token.split(':')
            if VALID_API_KEYS.get(api_key) == api_secret:
                return True
        except:
            pass
    
    return False


def generate_doc_name(doctype):
    """Generate a document name like ERPNext does"""
    counter = counters[doctype]
    counters[doctype] += 1
    
    if doctype == 'Customer':
        return f"CUST-{counter:05d}"
    elif doctype == 'Journal Entry':
        return f"ACC-JV-{datetime.now().year}-{counter:05d}"
    elif doctype == 'Purchase Invoice':
        return f"ACC-PINV-{datetime.now().year}-{counter:05d}"
    elif doctype == 'Payment Entry':
        return f"ACC-PAY-{datetime.now().year}-{counter:05d}"
    
    return f"{doctype}-{counter}"


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
    
    if doctype not in documents:
        return jsonify({
            'exc': f'DocType {doctype} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    # Get query parameters
    fields = request.args.get('fields', '["name"]')
    limit_start = int(request.args.get('limit_start', 0))
    limit_page_length = int(request.args.get('limit_page_length', 20))
    
    # Return list of documents
    doc_list = list(documents[doctype].values())
    paginated = doc_list[limit_start:limit_start + limit_page_length]
    
    return jsonify({
        'data': paginated
    })


@app.route('/api/resource/<doctype>/<name>', methods=['GET'])
def get_resource(doctype, name):
    """GET /api/resource/{doctype}/{name} - Get single resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    if doctype not in documents:
        return jsonify({
            'exc': f'DocType {doctype} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    if name not in documents[doctype]:
        return jsonify({
            'exc': f'{doctype} {name} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    return jsonify({
        'data': documents[doctype][name]
    })


@app.route('/api/resource/Customer', methods=['POST'])
def create_customer():
    """POST /api/resource/Customer - Create customer"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('customer_name'):
        return jsonify({
            'exc': 'Mandatory field customer_name missing',
            'exc_type': 'ValidationError'
        }), 400
    
    # Generate document name
    doc_name = generate_doc_name('Customer')
    
    # Create customer document
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
        'docstatus': 0  # 0 = Draft, 1 = Submitted, 2 = Cancelled
    }
    
    # Store customer
    documents['Customer'][doc_name] = customer
    
    return jsonify({
        'data': customer
    }), 201


@app.route('/api/resource/Journal Entry', methods=['POST'])
def create_journal_entry():
    """POST /api/resource/Journal Entry - Create journal entry"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    # Validate required fields
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
    
    # Validate that debits = credits
    total_debit = sum(acc.get('debit_in_account_currency', 0) for acc in data['accounts'])
    total_credit = sum(acc.get('credit_in_account_currency', 0) for acc in data['accounts'])
    
    if abs(total_debit - total_credit) > 0.01:
        return jsonify({
            'exc': f'Debit ({total_debit}) must equal Credit ({total_credit})',
            'exc_type': 'ValidationError'
        }), 400
    
    # Generate document name
    doc_name = generate_doc_name('Journal Entry')
    
    # Create journal entry document
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
    
    # Store journal entry
    documents['Journal Entry'][doc_name] = journal_entry
    
    return jsonify({
        'data': journal_entry
    }), 201


@app.route('/api/resource/Purchase Invoice', methods=['POST'])
def create_purchase_invoice():
    """POST /api/resource/Purchase Invoice - Create purchase invoice"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    # Validate required fields
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
    
    # Generate document name
    doc_name = generate_doc_name('Purchase Invoice')
    
    # Calculate totals
    total = sum(item.get('amount', 0) for item in data['items'])
    
    # Create purchase invoice document
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
    
    # Store purchase invoice
    documents['Purchase Invoice'][doc_name] = purchase_invoice
    
    return jsonify({
        'data': purchase_invoice
    }), 201


@app.route('/api/resource/Payment Entry', methods=['POST'])
def create_payment_entry():
    """POST /api/resource/Payment Entry - Create payment entry"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    data = request.get_json()
    
    # Validate required fields
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
    
    # Generate document name
    doc_name = generate_doc_name('Payment Entry')
    
    # Create payment entry document
    payment_entry = {
        'name': doc_name,
        'doctype': 'Payment Entry',
        'payment_type': data.get('payment_type'),  # Receive, Pay
        'party_type': data.get('party_type'),  # Customer, Supplier
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
    
    # Store payment entry
    documents['Payment Entry'][doc_name] = payment_entry
    
    return jsonify({
        'data': payment_entry
    }), 201


@app.route('/api/resource/<doctype>/<name>', methods=['PUT'])
def update_resource(doctype, name):
    """PUT /api/resource/{doctype}/{name} - Update resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    if doctype not in documents:
        return jsonify({
            'exc': f'DocType {doctype} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    if name not in documents[doctype]:
        return jsonify({
            'exc': f'{doctype} {name} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    data = request.get_json()
    
    # Update document
    documents[doctype][name].update(data)
    documents[doctype][name]['modified'] = datetime.now().isoformat()
    
    return jsonify({
        'data': documents[doctype][name]
    })


@app.route('/api/resource/<doctype>/<name>', methods=['DELETE'])
def delete_resource(doctype, name):
    """DELETE /api/resource/{doctype}/{name} - Delete resource"""
    if not authenticate():
        return jsonify({
            'exc': 'Authentication failed',
            'exc_type': 'AuthenticationError'
        }), 401
    
    if doctype not in documents:
        return jsonify({
            'exc': f'DocType {doctype} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    if name not in documents[doctype]:
        return jsonify({
            'exc': f'{doctype} {name} not found',
            'exc_type': 'DoesNotExistError'
        }), 404
    
    # Delete document
    del documents[doctype][name]
    
    return jsonify({
        'message': 'ok'
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'ERPNext Mock API is running',
        'documents_count': {
            doctype: len(docs) for doctype, docs in documents.items()
        }
    })


@app.route('/api/resource', methods=['GET'])
def list_doctypes():
    """List available doctypes"""
    return jsonify({
        'data': [
            {'name': 'Customer'},
            {'name': 'Journal Entry'},
            {'name': 'Purchase Invoice'},
            {'name': 'Payment Entry'}
        ]
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
        'exc': 'Internal Server Error',
        'exc_type': 'InternalError'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("ERPNext Mock API Server")
    print("=" * 60)
    print("\nAuthentication:")
    print("  API Key: test_api_key")
    print("  API Secret: test_api_secret")
    print("  Header: Authorization: token test_api_key:test_api_secret")
    print("\nAvailable Endpoints:")
    print("  GET  /api/method/frappe.auth.get_logged_user")
    print("  GET  /api/resource/Customer")
    print("  POST /api/resource/Customer")
    print("  GET  /api/resource/Journal Entry")
    print("  POST /api/resource/Journal Entry")
    print("  GET  /api/resource/Purchase Invoice")
    print("  POST /api/resource/Purchase Invoice")
    print("  GET  /api/resource/Payment Entry")
    print("  POST /api/resource/Payment Entry")
    print("  GET  /health")
    print("\nStarting server on http://localhost:8000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8000, debug=True)
