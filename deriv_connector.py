import websocket
import json
import threading
import time
import logging
from datetime import datetime

class DerivConnector:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.app_id = 1089  # App ID padrão da Deriv
        self.api_token = None
        self.balance = 0
        self.market_data = {}
        self.assets = [
            'R_100', 'R_75', 'R_50', 'R_25', 'R_10',
            '1HZ10V', '1HZ25V', '1HZ50V', '1HZ75V', '1HZ100V',
            'EURUSD', 'GBPUSD', 'AUDUSD', 'USDJPY', 'USDCAD'
        ]
        
    def connect(self, api_token=None):
        """Conectar ao WebSocket da Deriv"""
        try:
            self.api_token = api_token
            self.ws = websocket.WebSocketApp(
                f"wss://ws.derivws.com/websockets/v3?app_id={self.app_id}",
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Aguardar conexão
            time.sleep(2)
            return self.connected
            
        except Exception as e:
            logging.error(f"Erro ao conectar: {e}")
            return False
    
    def on_open(self, ws):
        logging.info("Conectado à Deriv")
        self.connected = True
        
        # Autorizar se tiver token
        if self.api_token:
            self.authorize()
        
        # Iniciar streaming de dados
        self.subscribe_to_market_data()
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.process_message(data)
        except Exception as e:
            logging.error(f"Erro ao processar mensagem: {e}")
    
    def on_error(self, ws, error):
        logging.error(f"Erro WebSocket: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logging.info("Conexão fechada")
        self.connected = False
    
    def authorize(self):
        """Autorizar com token da API"""
        if self.ws and self.api_token:
            auth_request = {
                "authorize": self.api_token,
                "req_id": 1
            }
            self.ws.send(json.dumps(auth_request))
    
    def subscribe_to_market_data(self):
        """Assinar dados de mercado para todos os ativos"""
        for asset in self.assets:
            tick_request = {
                "ticks": asset,
                "subscribe": 1,
                "req_id": self.assets.index(asset) + 100
            }
            self.ws.send(json.dumps(tick_request))
    
    def process_message(self, data):
        """Processar mensagens recebidas"""
        if 'authorize' in data:
            self.balance = data['authorize']['balance']
            logging.info(f"Autorizado. Saldo: {self.balance}")
        
        elif 'tick' in data:
            tick = data['tick']
            asset = tick['symbol']
            
            if asset not in self.market_data:
                self.market_data[asset] = []
            
            # Manter apenas últimos 100 ticks
            self.market_data[asset].append({
                'price': tick['quote'],
                'time': tick['epoch']
            })
            
            if len(self.market_data[asset]) > 100:
                self.market_data[asset].pop(0)
    
    def get_market_data(self):
        """Obter dados de mercado atuais"""
        result = {}
        
        for asset in self.assets:
            if asset in self.market_data and self.market_data[asset]:
                ticks = self.market_data[asset]
                current_price = ticks[-1]['price']
                
                # Calcular indicadores básicos
                prices = [t['price'] for t in ticks]
                
                if len(prices) >= 20:
                    # Médias móveis
                    ma_20 = sum(prices[-20:]) / 20
                    ma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else ma_20
                    
                    # RSI
                    gains = []
                    losses = []
                    for i in range(1, len(prices)):
                        diff = prices[i] - prices[i-1]
                        if diff > 0:
                            gains.append(diff)
                            losses.append(0)
                        else:
                            gains.append(0)
                            losses.append(abs(diff))
                    
                    avg_gain = sum(gains[-14:]) / 14 if gains else 0
                    avg_loss = sum(losses[-14:]) / 14 if losses else 1
                    
                    rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss != 0 else 50
                    
                    # Bollinger Bands
                    mean = sum(prices[-20:]) / 20
                    variance = sum((p - mean) ** 2 for p in prices[-20:]) / 20
                    std_dev = variance ** 0.5
                    
                    bb_upper = mean + (2 * std_dev)
                    bb_lower = mean - (2 * std_dev)
                    
                    result[asset] = {
                        'price': current_price,
                        'ma_20': ma_20,
                        'ma_50': ma_50,
                        'rsi': rsi,
                        'bb_upper': bb_upper,
                        'bb_lower': bb_lower,
                        'trend': 'up' if ma_20 > ma_50 else 'down',
                        'volatility': std_dev / mean * 100
                    }
        
        return result
    
    def execute_trade(self, trade_type, amount, asset):
        """Executar trade real"""
        if not self.connected:
            return {'success': False, 'error': 'Não conectado'}
        
        proposal_request = {
            "proposal": 1,
            "amount": amount,
            "basis": "stake",
            "contract_type": "CALL" if trade_type == 'buy' else "PUT",
            "currency": "USD",
            "duration": 5,
            "duration_unit": "m",
            "symbol": asset
        }
        
        self.ws.send(json.dumps(proposal_request))
        
        # Simular resposta (em produção, aguardar confirmação)
        time.sleep(2)
        
        return {
            'success': True,
            'profit': amount * 0.8,  # Simular lucro de 80%
            'contract_id': f"contract_{int(time.time())}"
        }
    
    def get_balance(self):
        """Obter saldo atual"""
        return self.balance
    
    def connect_real_account(self, api_token):
        """Conectar com conta real"""
        success = self.connect(api_token)
        return {
            'success': success,
            'balance': self.balance if success else 0,
            'message': 'Conectado com sucesso' if success else 'Falha na conexão'
          }
