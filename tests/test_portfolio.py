import unittest
from unittest.mock import patch, MagicMock

from AssetManager.assets import Asset
from AssetManager.portfolio import Portfolio, Possession

class TestPortfolio(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.initial_balance = 1000.0
        self.portfolio_map = {}
        self.portfolio = Portfolio(self.initial_balance, self.portfolio_map)
    
    def test_init(self):
        """Test Portfolio initialization."""
        self.assertEqual(self.portfolio.balance, 1000.0)
        self.assertEqual(self.portfolio.portfolio_map, {})
    
    def test_get_balance(self):
        """Test get_balance method."""
        result = self.portfolio.get_balance()
        expected = 'Your uninvested balance is $1000.00'
        self.assertEqual(result, expected)
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_buy_item_sufficient_balance(self, mock_price):
        """Test buying an item with sufficient balance."""
        mock_price.return_value = 50.0
        result = self.portfolio.buy_item('AAPL', 2)
        
        # Check that the balance was reduced
        self.assertEqual(self.portfolio.balance, 900.0)
        
        # Check that the possession was added
        self.assertIn('AAPL', self.portfolio.portfolio_map)
        self.assertEqual(self.portfolio.portfolio_map['AAPL'].quantity, 2)
        
        # Check return message
        expected_msg = 'Bought 2 units of AAPL at $100.00. Your new uninvested balance is $900.00.'
        self.assertEqual(result, expected_msg)
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_buy_item_insufficient_balance(self, mock_price):
        """Test buying an item with insufficient balance."""
        mock_price.return_value = 1500.0
        result = self.portfolio.buy_item('AAPL', 2)
        
        # Check that balance and portfolio were not changed
        self.assertEqual(self.portfolio.balance, 1000.0)
        self.assertEqual(len(self.portfolio.portfolio_map), 0)
        
        # Check return message
        self.assertEqual(result, 'Insufficient Balance')
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_buy_item_existing_ticker(self, mock_price):
        """Test buying an item that already exists in portfolio."""
        mock_price.return_value = 50.0
        # First buy
        self.portfolio.buy_item('AAPL', 2)
        
        # Second buy of same ticker
        mock_price.return_value = 60.0  # Different price for second buy
        result = self.portfolio.buy_item('AAPL', 1)
        
        # Check that possession quantity was updated
        self.assertEqual(self.portfolio.portfolio_map['AAPL'].quantity, 3)
        
        # Check return message
        expected_msg = 'Bought 1 units of AAPL at $60.00. Your new uninvested balance is $840.00.'
        self.assertEqual(result, expected_msg)
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_sell_item_not_in_portfolio(self, mock_price):
        """Test selling an item not in portfolio."""
        result = self.portfolio.sell_item('AAPL', 1)
        self.assertEqual(result, 'AAPL not in portfolio')
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_sell_item_insufficient_quantity(self, mock_price):
        """Test selling more than available quantity."""
        mock_price.return_value = 50.0
        # First buy to have some quantity
        self.portfolio.buy_item('AAPL', 2)
        
        # Try to sell more than available
        mock_price.return_value = 60.0
        result = self.portfolio.sell_item('AAPL', 5)
        
        # Check return message
        self.assertEqual(result, 'Only 2.00 units of AAPL is available to sell')
    
    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_sell_item_success(self, mock_price):
        """Test successful selling of an item."""
        mock_price.return_value = 50.0
        # First buy to have some quantity
        self.portfolio.buy_item('AAPL', 2)
        
        # Sell some of it
        mock_price.return_value = 60.0
        result = self.portfolio.sell_item('AAPL', 1)
        
        # Check that balance was increased
        self.assertEqual(self.portfolio.balance, 960.0)
        
        # Check that possession quantity was reduced
        self.assertEqual(self.portfolio.portfolio_map['AAPL'].quantity, 1.0)
        
        # Check return message
        expected_msg = 'Sold 1 units of AAPL at $60.00. You new uninvested balance is $960.00.'
        self.assertEqual(result, expected_msg)

    @patch('AssetManager.portfolio.yahoo.real_time_price')
    def test_get_formatted_portfolio(self, mock_price):
        """Test get_formatted_portfolio method."""
        # Create a mock assets_map for testing
        assets_map = {
            'AAPL': Asset(name='Apple Inc.', ticker='AAPL'),
            'MSFT': Asset(name='Microsoft Corporation', ticker='NVDA')
        }

        mock_price.return_value = 2
        
        # Add some items to the portfolio
        self.portfolio.portfolio_map = {
            'AAPL': Possession(quantity=100.0),
            'MSFT': Possession(quantity=50.0)
        }
        
        result = self.portfolio.get_formatted_portfolio(assets_map)
        
        # Check that the format includes balance and assets
        self.assertIn('Balance: $1000.00', result)
        self.assertIn('Assets:', result)
        self.assertIn('AAPL (Apple Inc.): 100.00 <=> $200.00', result)
        self.assertIn('MSFT (Microsoft Corporation): 50.00 <=> $100.00', result)
        self.assertIn('Legend for assets:', result)

if __name__ == '__main__':
    unittest.main()