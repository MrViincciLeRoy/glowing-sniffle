"""
Test script for ERPNext Mock API
Tests all endpoints that your erpnext_connector uses
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://glowing-sniffle-ocpc.onrender.com"
API_KEY = "test_api_key"
API_SECRET = "test_api_secret"

# Headers
HEADERS = {
    'Authorization': f'token {API_KEY}:{API_SECRET}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(success, message):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")


def test_health():
    """Test health endpoint"""
    print_section("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Server is running: {data['message']}")
            print(f"   Documents: {data['documents_count']}")
            return True
        else:
            print_result(False, f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Connection error: {str(e)}")
        return False


def test_authentication():
    """Test authentication endpoint"""
    print_section("Authentication Test")
    try:
        # Valid auth
        response = requests.get(
            f"{BASE_URL}/api/method/frappe.auth.get_logged_user",
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Authenticated as: {data['message']}")
        else:
            print_result(False, f"Valid auth failed: {response.status_code}")
            return False
        
        # Invalid auth
        bad_headers = {'Authorization': 'token bad:credentials'}
        response = requests.get(
            f"{BASE_URL}/api/method/frappe.auth.get_logged_user",
            headers=bad_headers
        )
        if response.status_code == 401:
            print_result(True, "Invalid credentials properly rejected")
        else:
            print_result(False, f"Invalid auth should return 401, got {response.status_code}")
        
        return True
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_create_customer():
    """Test customer creation (GET endpoint)"""
    print_section("Customer API Test")
    try:
        # Test GET (list customers)
        response = requests.get(
            f"{BASE_URL}/api/resource/Customer",
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Retrieved {len(data['data'])} customers")
        else:
            print_result(False, f"GET failed: {response.status_code}")
            return False
        
        # Test POST (create customer)
        customer_data = {
            'customer_name': 'Test Customer Ltd',
            'customer_type': 'Company',
            'email_id': 'test@customer.com',
            'mobile_no': '+27123456789'
        }
        response = requests.post(
            f"{BASE_URL}/api/resource/Customer",
            headers=HEADERS,
            json=customer_data
        )
        if response.status_code == 201:
            data = response.json()
            customer_name = data['data']['name']
            print_result(True, f"Created customer: {customer_name}")
            return customer_name
        else:
            print_result(False, f"POST failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_create_journal_entry():
    """Test journal entry creation (matches your erpnext_connector)"""
    print_section("Journal Entry API Test (Bank Transaction)")
    try:
        # This mimics what your erpnext_connector.create_journal_entry() does
        journal_data = {
            'doctype': 'Journal Entry',
            'company': 'Test Company',
            'posting_date': datetime.now().strftime('%Y-%m-%d'),
            'accounts': [
                {
                    'account': 'Bank Account - TC',
                    'debit_in_account_currency': 0,
                    'credit_in_account_currency': 1500.00,
                },
                {
                    'account': 'Transport Expenses - TC',
                    'debit_in_account_currency': 1500.00,
                    'credit_in_account_currency': 0,
                    'cost_center': 'Main - TC',
                }
            ],
            'user_remark': 'Uber ride to client meeting',
            'reference_number': 'TRANS-20241025-001',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/resource/Journal Entry",
            headers=HEADERS,
            json=journal_data
        )
        
        if response.status_code == 201:
            data = response.json()
            je_name = data['data']['name']
            print_result(True, f"Created journal entry: {je_name}")
            print(f"   Debit: R{data['data']['total_debit']:.2f}")
            print(f"   Credit: R{data['data']['total_credit']:.2f}")
            print(f"   Balanced: {data['data']['difference'] == 0}")
            return je_name
        else:
            print_result(False, f"POST failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_unbalanced_journal_entry():
    """Test that unbalanced entries are rejected"""
    print_section("Journal Entry Validation Test")
    try:
        # Create unbalanced entry (should fail)
        journal_data = {
            'company': 'Test Company',
            'posting_date': datetime.now().strftime('%Y-%m-%d'),
            'accounts': [
                {
                    'account': 'Bank Account - TC',
                    'debit_in_account_currency': 1000,
                    'credit_in_account_currency': 0,
                },
                {
                    'account': 'Expenses - TC',
                    'debit_in_account_currency': 0,
                    'credit_in_account_currency': 500,  # Unbalanced!
                }
            ],
        }
        
        response = requests.post(
            f"{BASE_URL}/api/resource/Journal Entry",
            headers=HEADERS,
            json=journal_data
        )
        
        if response.status_code == 400:
            print_result(True, "Unbalanced entry properly rejected")
            return True
        else:
            print_result(False, f"Should reject unbalanced entry, got {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_get_purchase_invoice():
    """Test purchase invoice API"""
    print_section("Purchase Invoice API Test")
    try:
        # Test GET
        response = requests.get(
            f"{BASE_URL}/api/resource/Purchase Invoice",
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Retrieved {len(data['data'])} purchase invoices")
            return True
        else:
            print_result(False, f"GET failed: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_create_payment_entry():
    """Test payment entry creation"""
    print_section("Payment Entry API Test")
    try:
        # Test POST
        payment_data = {
            'payment_type': 'Pay',
            'party_type': 'Supplier',
            'party': 'Test Supplier',
            'company': 'Test Company',
            'posting_date': datetime.now().strftime('%Y-%m-%d'),
            'paid_amount': 5000.00,
            'paid_from': 'Bank Account - TC',
            'paid_to': 'Creditors - TC',
            'reference_no': 'PAY-001',
        }
        
        response = requests.post(
            f"{BASE_URL}/api/resource/Payment Entry",
            headers=HEADERS,
            json=payment_data
        )
        
        if response.status_code == 201:
            data = response.json()
            payment_name = data['data']['name']
            print_result(True, f"Created payment entry: {payment_name}")
            print(f"   Amount: R{data['data']['paid_amount']:.2f}")
            return payment_name
        else:
            print_result(False, f"POST failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print_result(False, f"Error: {str(e)}")
        return False


def test_full_workflow():
    """Test a complete workflow mimicking your Odoo connector"""
    print_section("Full Workflow Test (Odoo → ERPNext)")
    
    print("\n📧 Simulating: Bank transaction from Gmail statement")
    print("   Transaction: Uber ride - R150.00 (Debit)")
    print("   Category: Transport")
    print("   Date: 2024-10-25")
    
    # Step 1: Create journal entry for the transaction
    journal_data = {
        'company': 'Test Company',
        'posting_date': '2024-10-25',
        'accounts': [
            {
                'account': 'Bank Account - TC',
                'debit_in_account_currency': 0,
                'credit_in_account_currency': 150.00,
            },
            {
                'account': 'Transport Expenses - TC',
                'debit_in_account_currency': 150.00,
                'credit_in_account_currency': 0,
                'cost_center': 'Main - TC',
            }
        ],
        'user_remark': 'Uber ride - auto-categorized from Gmail',
        'reference_number': 'BANK-TRANS-001',
    }
    
    print("\n⬆️  Syncing to ERPNext...")
    response = requests.post(
        f"{BASE_URL}/api/resource/Journal Entry",
        headers=HEADERS,
        json=journal_data
    )
    
    if response.status_code == 201:
        data = response.json()
        je_name = data['data']['name']
        print_result(True, f"Synced to ERPNext as {je_name}")
        
        # Verify we can retrieve it
        print("\n🔍 Verifying sync...")
        verify_response = requests.get(
            f"{BASE_URL}/api/resource/Journal Entry/{je_name}",
            headers=HEADERS
        )
        
        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            print_result(True, "Retrieved synced journal entry")
            print(f"   Status: {verify_data['data'].get('docstatus')}")
            print(f"   Total: R{verify_data['data']['total_debit']:.2f}")
            return True
        else:
            print_result(False, "Could not verify synced entry")
            return False
    else:
        print_result(False, f"Sync failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  ERPNext Mock API Test Suite")
    print("  Testing endpoints used by erpnext_connector")
    print("=" * 60)
    
    results = {
        'Health Check': test_health(),
        'Authentication': test_authentication(),
        'Customer API': test_create_customer() is not False,
        'Journal Entry': test_create_journal_entry() is not False,
        'Validation': test_unbalanced_journal_entry(),
        'Purchase Invoice': test_get_purchase_invoice(),
        'Payment Entry': test_create_payment_entry() is not False,
        'Full Workflow': test_full_workflow(),
    }
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your connector should work with this mock API.")
        print("\n📝 Configuration for Odoo:")
        print(f"   ERPNext URL: {BASE_URL}")
        print(f"   API Key: {API_KEY}")
        print(f"   API Secret: {API_SECRET}")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return passed == total


if __name__ == '__main__':
    import sys
    
    print("\n🚀 Starting ERPNext Mock API Tests...")
    print(f"📡 Target: {BASE_URL}")
    print(f"🔑 Using API Key: {API_KEY}")
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
