import requests
import sys
import json
from datetime import datetime
import time

class BidCaAPITester:
    def __init__(self, base_url="https://portfolio-176.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        self.test_user_id = None
        self.test_listing_id = None

    def log(self, message, status="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {status}: {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = self.session.headers.copy()
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}", "FAIL")
                try:
                    error_detail = response.json()
                    self.log(f"   Error: {error_detail}", "ERROR")
                except:
                    self.log(f"   Response: {response.text[:200]}", "ERROR")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Exception: {str(e)}", "FAIL")
            return False, {}

    def test_health_check(self):
        """Test API health endpoints"""
        self.log("=== HEALTH CHECK TESTS ===")
        
        # Test root endpoint
        self.run_test("Root API", "GET", "", 200)
        
        # Test health endpoint
        self.run_test("Health Check", "GET", "health", 200)

    def test_static_endpoints(self):
        """Test static data endpoints"""
        self.log("=== STATIC ENDPOINTS TESTS ===")
        
        # Test categories
        success, data = self.run_test("Get Categories", "GET", "categories", 200)
        if success and data.get("categories"):
            self.log(f"   Found {len(data['categories'])} categories")
        
        # Test cities
        success, data = self.run_test("Get Cities", "GET", "cities", 200)
        if success and data.get("cities"):
            self.log(f"   Found {len(data['cities'])} BC cities")

    def test_admin_login(self):
        """Test admin login"""
        self.log("=== ADMIN LOGIN TEST ===")
        
        admin_data = {
            "email": "admin@bidca.ca",
            "password": "admin123"
        }
        
        success, data = self.run_test("Admin Login", "POST", "auth/login", 200, admin_data)
        if success:
            self.log(f"   Admin logged in: {data.get('full_name')} ({data.get('role')})")
            return True
        return False

    def test_user_registration(self):
        """Test user registration with BC postal code validation"""
        self.log("=== USER REGISTRATION TESTS ===")
        
        # Test invalid postal code (non-BC)
        invalid_user = {
            "email": f"test_invalid_{int(time.time())}@example.com",
            "password": "testpass123",
            "full_name": "Test Invalid User",
            "city": "Vancouver",
            "postal_code": "M5V3A8"  # Toronto postal code
        }
        
        self.run_test("Invalid Postal Code", "POST", "auth/register", 400, invalid_user)
        
        # Test valid BC postal code
        valid_user = {
            "email": f"test_valid_{int(time.time())}@example.com",
            "password": "testpass123",
            "full_name": "Test Valid User",
            "city": "Vancouver",
            "postal_code": "V6B1A1"  # Valid BC postal code
        }
        
        success, data = self.run_test("Valid BC Registration", "POST", "auth/register", 200, valid_user)
        if success:
            self.test_user_id = data.get('id')
            self.log(f"   User registered: {data.get('full_name')} in {data.get('city')}")
            return True
        return False

    def test_user_login(self):
        """Test user login"""
        self.log("=== USER LOGIN TEST ===")
        
        # Test with wrong credentials
        wrong_creds = {
            "email": "wrong@example.com",
            "password": "wrongpass"
        }
        self.run_test("Wrong Credentials", "POST", "auth/login", 401, wrong_creds)
        
        # Test admin login
        admin_creds = {
            "email": "admin@bidca.ca",
            "password": "admin123"
        }
        success, data = self.run_test("Admin Login", "POST", "auth/login", 200, admin_creds)
        if success:
            self.log(f"   Admin role: {data.get('role')}")
            return True
        return False

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        self.log("=== AUTH ENDPOINTS TESTS ===")
        
        # Test /auth/me
        self.run_test("Get Current User", "GET", "auth/me", 200)
        
        # Test refresh token
        self.run_test("Refresh Token", "POST", "auth/refresh", 200)

    def test_listings_crud(self):
        """Test listings CRUD operations"""
        self.log("=== LISTINGS CRUD TESTS ===")
        
        # Test get listings
        success, data = self.run_test("Get Listings", "GET", "listings", 200)
        if success:
            self.log(f"   Found {data.get('total', 0)} listings")
        
        # Test get featured listings
        success, data = self.run_test("Get Featured Listings", "GET", "listings/featured", 200)
        if success:
            self.log(f"   Found {len(data.get('listings', []))} featured listings")
        
        # Test create listing (requires auth)
        listing_data = {
            "title": "Test Auction Item",
            "category": "Electronics",
            "description": "Test auction description",
            "city": "Vancouver",
            "starting_bid": 10.0,
            "bid_increment": 5.0,
            "duration_hours": 24,
            "listing_type": "auction"
        }
        
        success, data = self.run_test("Create Listing", "POST", "listings", 201, listing_data)
        if success:
            self.test_listing_id = data.get('_id')
            self.log(f"   Created listing: {data.get('title')}")

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        self.log("=== ADMIN ENDPOINTS TESTS ===")
        
        # Test admin stats
        self.run_test("Admin Stats", "GET", "admin/stats", 200)
        
        # Test admin listings
        self.run_test("Admin Listings", "GET", "admin/listings", 200)
        
        # Test admin users
        self.run_test("Admin Users", "GET", "admin/users", 200)
        
        # Test admin verifications
        self.run_test("Admin Verifications", "GET", "admin/verifications", 200)

    def test_brute_force_protection(self):
        """Test brute force protection"""
        self.log("=== BRUTE FORCE PROTECTION TEST ===")
        
        wrong_creds = {
            "email": "admin@bidca.ca",
            "password": "wrongpassword"
        }
        
        # Try 3 wrong attempts (should not be locked yet)
        for i in range(3):
            self.run_test(f"Wrong Attempt {i+1}", "POST", "auth/login", 401, wrong_creds)
        
        # Try 2 more (should trigger lockout after 5th)
        for i in range(2):
            self.run_test(f"Wrong Attempt {i+4}", "POST", "auth/login", 401, wrong_creds)
        
        # 6th attempt should be rate limited
        self.run_test("Rate Limited Attempt", "POST", "auth/login", 429, wrong_creds)

    def test_websocket_endpoints(self):
        """Test WebSocket related endpoints"""
        self.log("=== WEBSOCKET ENDPOINTS TESTS ===")
        
        # Test if Socket.IO endpoint is accessible
        try:
            response = self.session.get(f"{self.base_url}/api/socket.io/")
            if response.status_code in [200, 400]:  # 400 is expected for GET on socket.io
                self.log("✅ Socket.IO endpoint accessible", "PASS")
                self.tests_passed += 1
            else:
                self.log(f"❌ Socket.IO endpoint - Status: {response.status_code}", "FAIL")
        except Exception as e:
            self.log(f"❌ Socket.IO endpoint - Error: {str(e)}", "FAIL")
        
        self.tests_run += 1

    def test_cloudinary_signature(self):
        """Test Cloudinary signature endpoint (MOCKED)"""
        self.log("=== CLOUDINARY SIGNATURE TEST ===")
        
        success, data = self.run_test("Cloudinary Signature", "GET", "cloudinary/signature", 200)
        if success:
            if data.get('cloud_name') == 'mock_cloud_name':
                self.log("   ✅ MOCKED Cloudinary detected correctly", "PASS")
            else:
                self.log("   ⚠️  Cloudinary config may not be mocked", "WARN")

    def run_all_tests(self):
        """Run all tests"""
        self.log("🚀 Starting BidCa.ca API Tests")
        self.log(f"Testing against: {self.base_url}")
        
        try:
            # Basic health checks
            self.test_health_check()
            
            # Static endpoints
            self.test_static_endpoints()
            
            # Authentication tests
            if self.test_admin_login():
                self.test_auth_endpoints()
                self.test_admin_endpoints()
                self.test_cloudinary_signature()
            
            # User registration and login
            self.test_user_registration()
            self.test_user_login()
            
            # Listings tests
            self.test_listings_crud()
            
            # WebSocket tests
            self.test_websocket_endpoints()
            
            # Security tests
            self.test_brute_force_protection()
            
        except KeyboardInterrupt:
            self.log("Tests interrupted by user", "WARN")
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", "ERROR")
        
        # Print results
        self.log("=" * 50)
        self.log(f"📊 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"📈 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            self.log("🎉 Backend API tests mostly successful!", "SUCCESS")
            return 0
        elif success_rate >= 60:
            self.log("⚠️  Backend API has some issues", "WARN")
            return 1
        else:
            self.log("❌ Backend API has significant issues", "FAIL")
            return 2

def main():
    tester = BidCaAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())