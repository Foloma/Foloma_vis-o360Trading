import requests
import json
import time
import hashlib
import hmac
import base64

class DerivAPI:
    def __init__(self, app_id=1089):
        self.app_id = app_id
        self.base_url = "https://api.deriv.com/api/v3"
        self.ws_url = f"wss://ws.derivws.com/websockets/v3?app_id={app_id}"
        self.api_token = None
        
    def authenticate(self, api_token):
        """Autenticar na API da Deriv"""
        self.api_token = api_token
        return True
    
    def get_asset_list(self):
        """Obter lista de ativos disponíveis"""
        assets = [
            {"symbol": "R_100", "name": "Volatility 100 Index"},
            {"symbol": "R_75", "name": "Volatility 75 Index"},
            {"symbol": "R_50", "name": "Volatility 50 Index"},
            {"symbol": "R_25", "name": "Volatility 25 Index"},
            {"symbol": "R_10", "name": "Volatility 10 Index"},
            {"symbol": "1HZ10V", "name": "Step Index 10"},
            {"symbol": "1HZ25V", "name": "Step Index 25"},
            {"symbol": "1HZ50V", "name": "Step Index 50"},
            {"symbol": "1HZ75V", "name": "Step Index 75"},
            {"symbol": "1HZ100V", "name": "Step Index 100"},
            {"symbol": "EURUSD", "name": "EUR/USD"},
            {"symbol": "GBPUSD", "name": "GBP/USD"},
            {"symbol": "AUDUSD", "name": "AUD/USD"},
            {"symbol": "USDJPY", "name": "USD/JPY"},
            {"symbol": "USDCAD", "name": "USD/CAD"},
            {"symbol": "BTCUSD", "name": "Bitcoin/USD"},
            {"symbol": "ETHUSD", "name": "Ethereum/USD"}
        ]
        return assets
    
    def get_tick_history(self, symbol, count=1000):
        """Obter histórico de ticks para um símbolo"""
        # Simulação - em produção, faria chamada real à API
        import random
        import math
        
        ticks = []
        base_price = 100.0 if 'R_' in symbol else 1.2000
        
        for i in range(count):
            # Simular movimento de preço
            change = random.gauss(0, 0.5) if 'R_' in symbol else random.gauss(0, 0.001)
            price = base_price + change + math.sin(i/10) * 0.1
            
            ticks.append({
                'epoch': int(time.time()) - (count - i) * 60,
                'quote': round(price, 5),
                'symbol': symbol
            })
            
            base_price = price
        
        return ticks
    
    def get_contract_proposal(self, symbol, contract_type, amount, duration=5):
        """Obter proposta de contrato"""
        # Simulação - em produção, faria chamada real à API
        payout = amount * 1.8 if contract_type == "CALL" else amount * 1.7
        
        return {
            'proposal': {
                'longcode': f"{contract_type} {symbol}",
                'payout': payout,
                'spot': 100.00,
                'spot_time': int(time.time())
            }
        }
    
    def buy_contract(self, proposal_id, price):
        """Comprar contrato"""
        # Simulação - em produção, faria chamada real à API
        return {
            'buy': {
                'contract_id': f"contract_{int(time.time())}",
                'longcode': "Contract purchased",
                'payout': price * 1.8,
                'purchase_time': int(time.time())
            }
        }
    
    def get_balance(self):
        """Obter saldo da conta"""
        # Simulação - em produção, faria chamada real à API
        return {
            'balance': {
                'amount': 10000.00,
                'currency': 'USD'
            }
        }
    
    def sell_contract(self, contract_id):
        """Vender contrato antes do vencimento"""
        # Simulação
        return {
            'sell': {
                'contract_id': contract_id,
                'sold_for': 50.00
            }
        }
    
    def get_profit_table(self, limit=50):
        """Obter tabela de lucros"""
        # Simulação
        import random
        
        profits = []
        for i in range(limit):
            profit = random.uniform(-100, 200)
            profits.append({
                'contract_id': f"contract_{i}",
                'profit': profit,
                'timestamp': int(time.time()) - i * 3600
            })
        
        return profits
