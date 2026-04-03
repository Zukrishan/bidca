"""
BidCa.ca Feature Tests - Iteration 3
Tests for:
1. Brute force protection (5th attempt returns 429)
2. Admin stats endpoint (GMV, platform_revenue, pending_reports)
3. Normal login after brute force test
4. /api/users/me/bids endpoint (KeyError fix)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestBruteForceProtection:
    """Test brute force protection - 5th failed attempt should return 429"""
    
    @pytest.fixture(autouse=True)
    def clear_login_attempts(self):
        """Clear login attempts before each test"""
        # We'll use a unique email for each test run to avoid conflicts
        self.test_email = f"bruteforce_test_{int(time.time())}@test.com"
        yield
    
    def test_brute_force_returns_429_on_5th_attempt(self):
        """5th failed login attempt should return HTTP 429"""
        # Use a unique email that doesn't exist
        test_email = f"bruteforce_{int(time.time())}@nonexistent.com"
        
        # First 4 attempts should return 401
        for i in range(4):
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": test_email, "password": "wrongpassword"}
            )
            assert response.status_code == 401, f"Attempt {i+1}: Expected 401, got {response.status_code}"
            print(f"Attempt {i+1}: Got expected 401")
        
        # 5th attempt should return 429
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": "wrongpassword"}
        )
        assert response.status_code == 429, f"5th attempt: Expected 429, got {response.status_code}"
        print(f"5th attempt: Got expected 429 - Brute force protection working!")
        
        # Verify response message
        data = response.json()
        assert "Too many login attempts" in data.get("detail", ""), f"Expected 'Too many login attempts' message, got: {data}"


class TestAdminStats:
    """Test admin stats endpoint returns GMV and platform_revenue"""
    
    @pytest.fixture
    def admin_session(self):
        """Get authenticated admin session"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@bidca.ca", "password": "admin123"}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return session
    
    def test_admin_stats_contains_gmv(self, admin_session):
        """Admin stats should include total_gmv field"""
        response = admin_session.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_gmv" in data, f"Missing 'total_gmv' field in response: {data.keys()}"
        print(f"total_gmv: {data['total_gmv']}")
    
    def test_admin_stats_contains_platform_revenue(self, admin_session):
        """Admin stats should include platform_revenue field (should be 0 - free)"""
        response = admin_session.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "platform_revenue" in data, f"Missing 'platform_revenue' field in response: {data.keys()}"
        assert data["platform_revenue"] == 0, f"Platform revenue should be 0 (free), got: {data['platform_revenue']}"
        print(f"platform_revenue: {data['platform_revenue']} (Free as expected)")
    
    def test_admin_stats_contains_pending_reports(self, admin_session):
        """Admin stats should include pending_reports field"""
        response = admin_session.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "pending_reports" in data, f"Missing 'pending_reports' field in response: {data.keys()}"
        print(f"pending_reports: {data['pending_reports']}")
    
    def test_admin_stats_all_fields(self, admin_session):
        """Verify all expected admin stats fields are present"""
        response = admin_session.get(f"{BASE_URL}/api/admin/stats")
        assert response.status_code == 200
        
        data = response.json()
        expected_fields = [
            "total_users", "total_listings", "active_auctions", 
            "pending_listings", "pending_verifications", "total_bids",
            "total_transactions", "pending_reports", "total_gmv", "platform_revenue"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"All admin stats fields present: {list(data.keys())}")


class TestNormalLoginAfterBruteForce:
    """Test that normal login works with correct credentials"""
    
    def test_admin_login_works(self):
        """Admin login should work with correct credentials"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@bidca.ca", "password": "admin123"}
        )
        
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert data.get("email") == "admin@bidca.ca"
        assert data.get("role") == "admin"
        print(f"Admin login successful: {data.get('full_name')}")


class TestUserBidsEndpoint:
    """Test /api/users/me/bids endpoint - KeyError fix verification"""
    
    @pytest.fixture
    def admin_session(self):
        """Get authenticated admin session"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@bidca.ca", "password": "admin123"}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return session
    
    def test_my_bids_endpoint_no_keyerror(self, admin_session):
        """GET /api/users/me/bids should not throw KeyError"""
        response = admin_session.get(f"{BASE_URL}/api/users/me/bids")
        
        # Should return 200, not 500 (which would indicate KeyError)
        assert response.status_code == 200, f"Expected 200, got {response.status_code} - {response.text}"
        
        data = response.json()
        assert "bids" in data, f"Missing 'bids' field in response"
        print(f"My bids endpoint working, returned {len(data['bids'])} bids")


class TestHealthAndBasicEndpoints:
    """Basic health and endpoint tests"""
    
    def test_health_endpoint(self):
        """Health endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health check passed")
    
    def test_categories_endpoint(self):
        """Categories endpoint should return categories"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        print(f"Categories: {len(data['categories'])} categories available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
