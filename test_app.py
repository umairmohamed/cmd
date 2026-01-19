import unittest
from app import app, db, User, Customer

class CustomerSystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def register(self, username, password):
        return self.app.post('/register', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_auth(self):
        rv = self.register('admin', 'password')
        self.assertIn(b'Registration successful', rv.data)
        rv = self.login('admin', 'password')
        self.assertIn(b'Welcome, admin', rv.data)
        rv = self.logout()
        self.assertIn(b'Login', rv.data)

    def test_add_customer(self):
        self.register('admin', 'password')
        self.login('admin', 'password')

        # Test valid customer
        rv = self.app.post('/add_customer', data=dict(
            name='John Doe',
            mobile='123456789',
            initial_credit=100.0
        ), follow_redirects=True)
        self.assertIn(b'Customer added successfully!', rv.data)
        self.assertIn(b'John Doe', rv.data)
        self.assertIn(b'123456789', rv.data)

        # Test invalid mobile (8 digits)
        rv = self.app.post('/add_customer', data=dict(
            name='Jane Doe',
            mobile='12345678',
            initial_credit=100.0
        ), follow_redirects=True)
        self.assertIn(b'Invalid mobile number', rv.data)

        # Test invalid mobile (10 digits)
        rv = self.app.post('/add_customer', data=dict(
            name='Jane Doe',
            mobile='1234567890',
            initial_credit=100.0
        ), follow_redirects=True)
        self.assertIn(b'Invalid mobile number', rv.data)

    def test_payment(self):
        self.register('admin', 'password')
        self.login('admin', 'password')

        # Add customer with 1000 credit
        self.app.post('/add_customer', data=dict(
            name='John Doe',
            mobile='123456789',
            initial_credit=1000.0
        ), follow_redirects=True)

        with app.app_context():
            customer = Customer.query.filter_by(mobile='123456789').first()
            customer_id = customer.id

        # Add payment of 200
        rv = self.app.post(f'/add_payment/{customer_id}', json={'amount': 200})
        data = rv.get_json()

        self.assertTrue(data['success'])
        self.assertEqual(data['new_balance'], 800.0)
        self.assertEqual(data['total_credit'], 800.0)

        # Add another payment of 800
        rv = self.app.post(f'/add_payment/{customer_id}', json={'amount': 800})
        data = rv.get_json()
        self.assertEqual(data['new_balance'], 0.0)
        self.assertEqual(data['total_credit'], 0.0)

if __name__ == '__main__':
    unittest.main()
