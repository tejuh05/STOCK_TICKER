import heapq
import random
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
import os


class Stock:
    """Represents a stock with its properties"""
    def __init__(self, symbol: str, name: str, current_price: float, volume: int = 0):
        self.symbol = symbol
        self.name = name
        self.current_price = current_price
        self.previous_price = current_price
        self.volume = volume
        self.price_history = deque(maxlen=20)  # Keep last 20 prices for trend
        self.price_history.append(current_price)
        self.last_updated = datetime.now()
        self.daily_high = current_price
        self.daily_low = current_price
    
    def update_price(self, new_price: float, volume: int = 0):
        """Update stock price and maintain history"""
        self.previous_price = self.current_price
        self.current_price = new_price
        self.volume += volume
        self.price_history.append(new_price)
        self.last_updated = datetime.now()
        
        # Update daily high/low
        self.daily_high = max(self.daily_high, new_price)
        self.daily_low = min(self.daily_low, new_price)
    
    def get_percentage_change(self) -> float:
        """Calculate percentage change from previous price"""
        if self.previous_price == 0:
            return 0.0
        return ((self.current_price - self.previous_price) / self.previous_price) * 100
    
    def get_trend(self) -> str:
        """Get price trend based on recent history"""
        if len(self.price_history) < 3:
            return "STABLE"
        
        recent = list(self.price_history)[-3:]
        if recent[2] > recent[1] > recent[0]:
            return "📈 UPTREND"
        elif recent[2] < recent[1] < recent[0]:
            return "📉 DOWNTREND"
        else:
            return "📊 STABLE"
    
    def __str__(self):
        change = self.get_percentage_change()
        trend = self.get_trend()
        return f"{self.symbol} | ${self.current_price:.2f} | {change:+.2f}% | {trend}"


class OrderBookEntry:
    """Represents an order in the order book"""
    def __init__(self, order_id: str, symbol: str, order_type: str, 
                 price: float, quantity: int, user_id: str = "USER"):
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type  # 'BUY' or 'SELL'
        self.price = price
        self.quantity = quantity
        self.user_id = user_id
        self.timestamp = datetime.now()
    
    def __lt__(self, other):
        """Comparison for heap operations"""
        if self.order_type == 'BUY':
            # For buy orders: higher price has higher priority
            if self.price != other.price:
                return self.price > other.price
            return self.timestamp < other.timestamp
        else:
            # For sell orders: lower price has higher priority
            if self.price != other.price:
                return self.price < other.price
            return self.timestamp < other.timestamp


class PriceAlert:
    """Represents a price alert"""
    def __init__(self, alert_id: str, symbol: str, target_price: float, 
                 alert_type: str, user_id: str = "USER"):
        self.alert_id = alert_id
        self.symbol = symbol
        self.target_price = target_price
        self.alert_type = alert_type  # 'ABOVE' or 'BELOW'
        self.user_id = user_id
        self.created_at = datetime.now()
        self.triggered = False
    
    def __lt__(self, other):
        """Comparison for heap operations"""
        return self.target_price < other.target_price
    
    def check_trigger(self, current_price: float) -> bool:
        """Check if alert should be triggered"""
        if self.triggered:
            return False
        
        if self.alert_type == 'ABOVE' and current_price >= self.target_price:
            self.triggered = True
            return True
        elif self.alert_type == 'BELOW' and current_price <= self.target_price:
            self.triggered = True
            return True
        return False


class InteractiveStockTicker:
    """Interactive Stock Ticker System with User Control"""
    
    def __init__(self):
        # Stock data storage
        self.stocks: Dict[str, Stock] = {}
        
        # Heaps for market analysis
        self.gainers_heap = []
        self.losers_heap = []
        self.volatile_heap = []
        
        # Order book - separate heaps for buy/sell orders
        self.order_books: Dict[str, Dict[str, List]] = defaultdict(lambda: {'BUY': [], 'SELL': []})
        
        # Price alerts
        self.price_alerts = []
        self.triggered_alerts = []
        
        # User portfolio and transaction history
        self.user_portfolio = defaultdict(int)  # symbol -> quantity
        self.user_cash = 100000.0  # Starting with $100,000
        self.transaction_history = []
        
        # Market simulation
        self.market_open = False
        self.simulation_thread = None
        
        # Statistics
        self.total_operations = 0
        self.orders_placed = 0
        self.trades_executed = 0
        
        # Initialize with some stocks
        self._initialize_market()
    
    def _initialize_market(self):
        """Initialize market with popular stocks"""
        initial_stocks = [
            ("AAPL", "Apple Inc.", 175.50),
            ("GOOGL", "Alphabet Inc.", 2850.00),
            ("MSFT", "Microsoft Corp.", 380.25),
            ("TSLA", "Tesla Inc.", 850.75),
            ("AMZN", "Amazon.com Inc.", 3200.00),
            ("META", "Meta Platforms", 485.30),
            ("NVDA", "NVIDIA Corp.", 750.20),
            ("NFLX", "Netflix Inc.", 420.15),
            ("AMD", "Advanced Micro Devices", 140.80),
            ("INTC", "Intel Corp.", 55.90)
        ]
        
        for symbol, name, price in initial_stocks:
            self.stocks[symbol] = Stock(symbol, name, price)
            self._update_market_heaps(symbol)
    
    def _update_market_heaps(self, symbol: str):
        """Update market analysis heaps"""
        stock = self.stocks[symbol]
        change_pct = stock.get_percentage_change()
        
        # Add to heaps (we'll clean them periodically to avoid infinite growth)
        heapq.heappush(self.gainers_heap, (-change_pct, symbol, stock.current_price, datetime.now()))
        heapq.heappush(self.losers_heap, (change_pct, symbol, stock.current_price, datetime.now()))
        
        self.total_operations += 2
        
        # Keep heaps manageable
        if len(self.gainers_heap) > 50:
            self.gainers_heap = sorted(self.gainers_heap)[-25:]
            heapq.heapify(self.gainers_heap)
        
        if len(self.losers_heap) > 50:
            self.losers_heap = self.losers_heap[:25]
            heapq.heapify(self.losers_heap)
    
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display system header"""
        print("=" * 80)
        print("🏛️  INTERACTIVE STOCK TICKER SYSTEM")
        print("=" * 80)
        market_status = "🟢 OPEN" if self.market_open else "🔴 CLOSED"
        print(f"Market Status: {market_status} | Your Cash: ${self.user_cash:,.2f} | "
              f"Portfolio Value: ${self.get_portfolio_value():,.2f}")
        print("-" * 80)
    
    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value"""
        total_value = 0
        for symbol, quantity in self.user_portfolio.items():
            if symbol in self.stocks and quantity > 0:
                total_value += self.stocks[symbol].current_price * quantity
        return total_value
    
    def display_stocks(self):
        """Display current stock prices"""
        print("📊 CURRENT STOCK PRICES:")
        print("-" * 50)
        for symbol, stock in sorted(self.stocks.items()):
            owned = self.user_portfolio.get(symbol, 0)
            ownership = f" (You own: {owned})" if owned > 0 else ""
            print(f"  {stock}{ownership}")
    
    def get_market_leaders(self, k: int = 5) -> Tuple[List, List]:
        """Get top gainers and losers efficiently using heaps"""
        # Get gainers (clean up old entries)
        gainers = []
        temp_gainers = []
        current_time = datetime.now()
        
        while self.gainers_heap and len(gainers) < k:
            neg_change, symbol, price, timestamp = heapq.heappop(self.gainers_heap)
            # Only consider recent entries (last 5 minutes)
            if (current_time - timestamp).seconds < 300 and symbol in self.stocks:
                gainers.append((symbol, -neg_change, self.stocks[symbol].current_price))
                temp_gainers.append((neg_change, symbol, price, timestamp))
        
        # Restore heap
        for item in temp_gainers:
            heapq.heappush(self.gainers_heap, item)
        
        # Get losers
        losers = []
        temp_losers = []
        
        while self.losers_heap and len(losers) < k:
            change, symbol, price, timestamp = heapq.heappop(self.losers_heap)
            if (current_time - timestamp).seconds < 300 and symbol in self.stocks:
                losers.append((symbol, change, self.stocks[symbol].current_price))
                temp_losers.append((change, symbol, price, timestamp))
        
        # Restore heap
        for item in temp_losers:
            heapq.heappush(self.losers_heap, item)
        
        return gainers, losers
    
    def display_market_movers(self):
        """Display market leaders"""
        gainers, losers = self.get_market_leaders()
        
        print("\n🚀 TOP GAINERS:")
        for i, (symbol, change, price) in enumerate(gainers, 1):
            print(f"  {i}. {symbol}: ${price:.2f} (+{change:.2f}%)")
        
        if not gainers:
            print("  No significant gainers yet.")
        
        print("\n📉 TOP LOSERS:")
        for i, (symbol, change, price) in enumerate(losers, 1):
            print(f"  {i}. {symbol}: ${price:.2f} ({change:.2f}%)")
        
        if not losers:
            print("  No significant losers yet.")
    
    def buy_stock(self, symbol: str, quantity: int) -> bool:
        """Buy stock directly at market price"""
        if symbol not in self.stocks:
            print(f"❌ Stock {symbol} not found!")
            return False
        
        stock = self.stocks[symbol]
        total_cost = stock.current_price * quantity
        
        if total_cost > self.user_cash:
            print(f"❌ Insufficient funds! You need ${total_cost:,.2f} but have ${self.user_cash:,.2f}")
            return False
        
        # Execute purchase
        self.user_cash -= total_cost
        self.user_portfolio[symbol] += quantity
        
        # Record transaction
        transaction = {
            'type': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': stock.current_price,
            'total': total_cost,
            'timestamp': datetime.now()
        }
        self.transaction_history.append(transaction)
        self.trades_executed += 1
        
        print(f"✅ Bought {quantity} shares of {symbol} at ${stock.current_price:.2f} each")
        print(f"💰 Total cost: ${total_cost:,.2f} | Remaining cash: ${self.user_cash:,.2f}")
        return True
    
    def sell_stock(self, symbol: str, quantity: int) -> bool:
        """Sell stock directly at market price"""
        if symbol not in self.stocks:
            print(f"❌ Stock {symbol} not found!")
            return False
        
        if self.user_portfolio.get(symbol, 0) < quantity:
            print(f"❌ You don't have enough shares! You own {self.user_portfolio.get(symbol, 0)} shares.")
            return False
        
        stock = self.stocks[symbol]
        total_revenue = stock.current_price * quantity
        
        # Execute sale
        self.user_cash += total_revenue
        self.user_portfolio[symbol] -= quantity
        
        # Record transaction
        transaction = {
            'type': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': stock.current_price,
            'total': total_revenue,
            'timestamp': datetime.now()
        }
        self.transaction_history.append(transaction)
        self.trades_executed += 1
        
        print(f"✅ Sold {quantity} shares of {symbol} at ${stock.current_price:.2f} each")
        print(f"💰 Total revenue: ${total_revenue:,.2f} | New cash balance: ${self.user_cash:,.2f}")
        return True
    
    def place_limit_order(self, symbol: str, order_type: str, price: float, quantity: int) -> bool:
        """Place a limit order in the order book"""
        if symbol not in self.stocks:
            print(f"❌ Stock {symbol} not found!")
            return False
        
        # Check if user has sufficient funds/shares
        if order_type == 'BUY':
            total_cost = price * quantity
            if total_cost > self.user_cash:
                print(f"❌ Insufficient funds for limit order!")
                return False
        else:  # SELL
            if self.user_portfolio.get(symbol, 0) < quantity:
                print(f"❌ You don't have enough shares to sell!")
                return False
        
        order_id = f"{order_type}_{symbol}_{int(time.time())}"
        order = OrderBookEntry(order_id, symbol, order_type, price, quantity)
        
        # Add to order book heap
        heapq.heappush(self.order_books[symbol][order_type], order)
        self.orders_placed += 1
        self.total_operations += 1
        
        print(f"✅ Limit order placed: {order_type} {quantity} {symbol} @ ${price:.2f}")
        
        # Try to match orders
        self._match_orders(symbol)
        return True
    
    def _match_orders(self, symbol: str):
        """Match buy and sell orders for a symbol"""
        buy_orders = self.order_books[symbol]['BUY']
        sell_orders = self.order_books[symbol]['SELL']
        
        matches_found = 0
        while buy_orders and sell_orders:
            best_buy = buy_orders[0]
            best_sell = sell_orders[0]
            
            # Check if orders can match (buy price >= sell price)
            if best_buy.price >= best_sell.price:
                # Remove matched orders
                buy_order = heapq.heappop(buy_orders)
                sell_order = heapq.heappop(sell_orders)
                
                # Execute trade
                trade_price = (buy_order.price + sell_order.price) / 2
                trade_quantity = min(buy_order.quantity, sell_order.quantity)
                
                # Update stock price based on trade
                self.stocks[symbol].update_price(trade_price, trade_quantity)
                self._update_market_heaps(symbol)
                
                # Update user portfolio if they were involved
                if buy_order.user_id == "USER":
                    total_cost = trade_price * trade_quantity
                    self.user_cash -= total_cost
                    self.user_portfolio[symbol] += trade_quantity
                
                if sell_order.user_id == "USER":
                    total_revenue = trade_price * trade_quantity
                    self.user_cash += total_revenue
                    self.user_portfolio[symbol] -= trade_quantity
                
                matches_found += 1
                self.trades_executed += 1
                
                print(f"🎯 ORDER MATCHED: {trade_quantity} shares of {symbol} at ${trade_price:.2f}")
                
                # Handle partial fills
                if buy_order.quantity > trade_quantity:
                    buy_order.quantity -= trade_quantity
                    heapq.heappush(buy_orders, buy_order)
                
                if sell_order.quantity > trade_quantity:
                    sell_order.quantity -= trade_quantity
                    heapq.heappush(sell_orders, sell_order)
                
                # Check price alerts
                self._check_price_alerts(symbol, trade_price)
            else:
                break
        
        if matches_found > 0:
            print(f"📊 {matches_found} order(s) matched for {symbol}")
    
    def set_price_alert(self, symbol: str, target_price: float, alert_type: str) -> bool:
        """Set a price alert"""
        if symbol not in self.stocks:
            print(f"❌ Stock {symbol} not found!")
            return False
        
        alert_id = f"ALERT_{symbol}_{int(time.time())}"
        alert = PriceAlert(alert_id, symbol, target_price, alert_type)
        
        heapq.heappush(self.price_alerts, alert)
        self.total_operations += 1
        
        print(f"🔔 Alert set: {symbol} {alert_type} ${target_price:.2f}")
        return True
    
    def _check_price_alerts(self, symbol: str, current_price: float):
        """Check price alerts for triggers"""
        triggered_count = 0
        remaining_alerts = []
        
        while self.price_alerts:
            alert = heapq.heappop(self.price_alerts)
            if alert.symbol == symbol and alert.check_trigger(current_price):
                self.triggered_alerts.append(alert)
                print(f"🚨 ALERT TRIGGERED: {symbol} hit ${current_price:.2f} (Target: {alert.alert_type} ${alert.target_price:.2f})")
                triggered_count += 1
            elif not alert.triggered:
                remaining_alerts.append(alert)
        
        # Restore non-triggered alerts
        for alert in remaining_alerts:
            heapq.heappush(self.price_alerts, alert)
        
        return triggered_count
    
    def start_market_simulation(self):
        """Start background market simulation"""
        if self.market_open:
            print("⚠️  Market is already open!")
            return
        
        self.market_open = True
        
        def simulate_market():
            while self.market_open:
                # Randomly update 2-3 stock prices
                symbols_to_update = random.sample(list(self.stocks.keys()), random.randint(2, 4))
                
                for symbol in symbols_to_update:
                    stock = self.stocks[symbol]
                    # Random price movement (-3% to +3%)
                    change_pct = random.uniform(-3, 3)
                    new_price = stock.current_price * (1 + change_pct / 100)
                    new_price = max(new_price, 1.0)  # Don't let stocks go below $1
                    
                    volume = random.randint(1000, 50000)
                    stock.update_price(new_price, volume)
                    
                    self._update_market_heaps(symbol)
                    self._check_price_alerts(symbol, new_price)
                
                # Process some AI orders to create market activity
                self._generate_ai_orders()
                
                time.sleep(3)  # Update every 3 seconds
        
        self.simulation_thread = threading.Thread(target=simulate_market)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        print("🟢 Market opened! Prices will update automatically every 3 seconds.")
    
    def _generate_ai_orders(self):
        """Generate AI orders to create market activity"""
        if random.random() < 0.3:  # 30% chance to place AI orders
            symbol = random.choice(list(self.stocks.keys()))
            stock = self.stocks[symbol]
            
            order_type = random.choice(['BUY', 'SELL'])
            # AI orders are slightly away from current price
            price_offset = random.uniform(-2, 2)  # Within 2% of current price
            order_price = stock.current_price * (1 + price_offset / 100)
            quantity = random.randint(10, 100)
            
            order_id = f"AI_{order_type}_{symbol}_{int(time.time())}"
            order = OrderBookEntry(order_id, symbol, order_type, order_price, quantity, "AI")
            
            heapq.heappush(self.order_books[symbol][order_type], order)
            self._match_orders(symbol)
    
    def stop_market_simulation(self):
        """Stop market simulation"""
        if not self.market_open:
            print("⚠️  Market is already closed!")
            return
        
        self.market_open = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1)
        print("🔴 Market closed!")
    
    def display_portfolio(self):
        """Display user's portfolio"""
        print("\n💼 YOUR PORTFOLIO:")
        print("-" * 50)
        total_value = 0
        
        for symbol, quantity in self.user_portfolio.items():
            if quantity > 0:
                current_price = self.stocks[symbol].current_price
                position_value = current_price * quantity
                total_value += position_value
                print(f"  {symbol}: {quantity} shares @ ${current_price:.2f} = ${position_value:,.2f}")
        
        print(f"\nCash: ${self.user_cash:,.2f}")
        print(f"Total Portfolio Value: ${total_value + self.user_cash:,.2f}")
        
        if self.transaction_history:
            print(f"\nRecent Transactions: {len(self.transaction_history)}")
    
    def display_order_book(self, symbol: str):
        """Display order book for a symbol"""
        if symbol not in self.stocks:
            print(f"❌ Stock {symbol} not found!")
            return
        
        print(f"\n📋 ORDER BOOK FOR {symbol}:")
        print("-" * 40)
        
        # Show buy orders (highest price first)
        buy_orders = sorted(self.order_books[symbol]['BUY'], reverse=True)[:5]
        print("BUY ORDERS (Best 5):")
        for i, order in enumerate(buy_orders, 1):
            print(f"  {i}. ${order.price:.2f} x {order.quantity} ({order.user_id})")
        
        if not buy_orders:
            print("  No buy orders")
        
        # Show current price
        current_price = self.stocks[symbol].current_price
        print(f"\n  --> CURRENT PRICE: ${current_price:.2f} <--")
        
        # Show sell orders (lowest price first)
        sell_orders = sorted(self.order_books[symbol]['SELL'])[:5]
        print("\nSELL ORDERS (Best 5):")
        for i, order in enumerate(sell_orders, 1):
            print(f"  {i}. ${order.price:.2f} x {order.quantity} ({order.user_id})")
        
        if not sell_orders:
            print("  No sell orders")
    
    def display_statistics(self):
        """Display system statistics"""
        print(f"\n📈 SYSTEM STATISTICS:")
        print(f"  Total Heap Operations: {self.total_operations:,}")
        print(f"  Orders Placed: {self.orders_placed}")
        print(f"  Trades Executed: {self.trades_executed}")
        print(f"  Active Price Alerts: {len(self.price_alerts)}")
        print(f"  Triggered Alerts: {len(self.triggered_alerts)}")
    
    def run_interactive_session(self):
        """Main interactive loop"""
        print("🎮 Welcome to the Interactive Stock Ticker!")
        print("This system demonstrates heap data structures in a real stock trading environment.")
        print("\nType 'help' to see available commands.")
        
        while True:
            try:
                print("\n" + "="*60)
                command = input("📝 Enter command (or 'help'): ").strip().lower()
                
                if command == 'help' or command == 'h':
                    self.show_help()
                elif command == 'status' or command == 's':
                    self.clear_screen()
                    self.display_header()
                    self.display_stocks()
                    self.display_market_movers()
                elif command == 'portfolio' or command == 'p':
                    self.display_portfolio()
                elif command.startswith('buy '):
                    parts = command.split()
                    if len(parts) == 3:
                        symbol, quantity = parts[1].upper(), int(parts[2])
                        self.buy_stock(symbol, quantity)
                    else:
                        print("Usage: buy SYMBOL QUANTITY")
                elif command.startswith('sell '):
                    parts = command.split()
                    if len(parts) == 3:
                        symbol, quantity = parts[1].upper(), int(parts[2])
                        self.sell_stock(symbol, quantity)
                    else:
                        print("Usage: sell SYMBOL QUANTITY")
                elif command.startswith('order '):
                    parts = command.split()
                    if len(parts) == 5:
                        _, order_type, symbol, price, quantity = parts
                        self.place_limit_order(symbol.upper(), order_type.upper(), float(price), int(quantity))
                    else:
                        print("Usage: order BUY/SELL SYMBOL PRICE QUANTITY")
                elif command.startswith('alert '):
                    parts = command.split()
                    if len(parts) == 4:
                        _, symbol, alert_type, price = parts
                        self.set_price_alert(symbol.upper(), float(price), alert_type.upper())
                    else:
                        print("Usage: alert SYMBOL ABOVE/BELOW PRICE")
                elif command.startswith('book '):
                    symbol = command.split()[1].upper()
                    self.display_order_book(symbol)
                elif command == 'open':
                    self.start_market_simulation()
                elif command == 'close':
                    self.stop_market_simulation()
                elif command == 'stats':
                    self.display_statistics()
                elif command == 'clear':
                    self.clear_screen()
                elif command == 'exit' or command == 'quit':
                    print("👋 Goodbye! Thanks for using the Interactive Stock Ticker!")
                    self.stop_market_simulation()
                    break
                else:
                    print("❌ Unknown command. Type 'help' for available commands.")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self.stop_market_simulation()
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_help(self):
        """Display help information"""
        print("\n🔧 AVAILABLE COMMANDS:")
        print("-" * 50)
        print("  status (s)           - Show market status and stock prices")
        print("  portfolio (p)        - Show your portfolio")
        print("  buy SYMBOL QTY       - Buy stock at market price")
        print("  sell SYMBOL QTY      - Sell stock at market price")
        print("  order TYPE SYMBOL PRICE QTY - Place limit order (BUY/SELL)")
        print("  alert SYMBOL ABOVE/BELOW PRICE - Set price alert")
        print("  book SYMBOL          - Show order book for stock")
        print("  open                 - Start market simulation")
        print("  close                - Stop market simulation")
        print("  stats                - Show system statistics")
        print("  clear                - Clear screen")
        print("  help (h)             - Show this help")
        print("  exit/quit            - Exit program")
        print("\n📚 EXAMPLES:")
        print("  buy AAPL 10          - Buy 10 shares of Apple")
        print("  order BUY TSLA 800 5 - Place limit order: Buy 5 Tesla @ $800")
        print("  alert MSFT ABOVE 400 - Alert when Microsoft goes above $400")


def main():
    """Main entry point"""
    ticker = InteractiveStockTicker()
    ticker.run_interactive_session()


if __name__ == "__main__":
    main()