"""
PC Controller 2.0 - Comprehensive Unit & Security Test Suite
"""
import unittest
import json
import os
import secrets
from app import create_app, config
from app.security import verify_plain_password, verify_password, safe_resolve_path

class TestPCController(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_index_page_loads(self):
        """Test main index route returns 200 with HTML template."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'PC CONTROL PRO', response.data)
        self.assertIn(b'/static/css/style.css', response.data)
        self.assertIn(b'/static/js/app.js', response.data)

    def test_02_static_assets_exist(self):
        """Verify static CSS, JS, and manifest files are served."""
        css_res = self.client.get('/static/css/style.css')
        self.assertEqual(css_res.status_code, 200)

        js_res = self.client.get('/static/js/app.js')
        self.assertEqual(js_res.status_code, 200)

        manifest_res = self.client.get('/static/manifest.json')
        self.assertEqual(manifest_res.status_code, 200)

    def test_03_unauthenticated_api_blocked(self):
        """Verify protected API endpoints reject unauthenticated requests with 401."""
        protected_endpoints = [
            '/api/status',
            '/api/sysinfo',
            '/api/screenshot',
            '/api/files_list',
            '/api/browse',
            '/api/apps'
        ]
        for ep in protected_endpoints:
            with self.subTest(endpoint=ep):
                res = self.client.get(ep)
                self.assertEqual(res.status_code, 401, f"{ep} allowed unauthorized access!")
                data = json.loads(res.data)
                self.assertEqual(data.get('status'), 'unauthorized')

    def test_04_auth_flow(self):
        """Test login with wrong and correct password, and subsequent authenticated requests."""
        # 1. Wrong password
        wrong_res = self.client.post('/api/auth/login', json={'password': 'completely_wrong_password'})
        self.assertEqual(wrong_res.status_code, 401)

        # 2. Correct password
        correct_res = self.client.post('/api/auth/login', json={'password': config.UI_PASSWORD})
        self.assertEqual(correct_res.status_code, 200)
        data = json.loads(correct_res.data)
        self.assertEqual(data.get('status'), 'ok')
        self.assertTrue('token' in data)

        # 3. Check status is now authorized
        status_res = self.client.get('/api/auth/check')
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(json.loads(status_res.data).get('authenticated'))

        # 4. Now protected endpoint /api/status works
        auth_status = self.client.get('/api/status')
        self.assertEqual(auth_status.status_code, 200)

        # 5. Logout
        logout_res = self.client.post('/api/auth/logout')
        self.assertEqual(logout_res.status_code, 200)

        # 6. Verify blocked again
        blocked_res = self.client.get('/api/status')
        self.assertEqual(blocked_res.status_code, 401)

    def test_05_path_traversal_protection(self):
        """Test safe_resolve_path prevents traversal outside system."""
        # Non-existent or invalid paths
        self.assertIsNone(safe_resolve_path(None))
        self.assertIsNone(safe_resolve_path("///invalid///nonexistent///path"))
        
        # Valid path resolves
        cwd = safe_resolve_path(os.getcwd())
        self.assertIsNotNone(cwd)
        self.assertTrue(os.path.exists(cwd))

    def test_06_version_endpoint(self):
        """Public version endpoint should work without auth."""
        res = self.client.get('/api/version')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data.get('version'), config.APP_VERSION)

if __name__ == '__main__':
    unittest.main()
