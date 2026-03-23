import json
import websocket
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DerivWebSocketClient:
    def __init__(self, config, on_tick_callback=None):
        self.config = config
        self.ws = None
        self.running = False
        self.on_tick_callback = on_tick_callback
        self.connected = False
        self.authorized = False
        self.balance = 0
        self.currency = 'USD'
        self.current_symbol = 'R_100'
        self.reconnect_attempts = 0
        self.loginid = ''
        self.balance_subscribed = False
        self.markup_percentage = 0.5
        self.trading_bot = None
        self.payment_system = None
        
    def set_trading_bot(self, bot):
        self.trading_bot = bot
        
    def set_payment_system(self, payment_system):
        self.payment_system = payment_system
        
    def connect(self):
        try:
            url = f"wss://ws.derivws.com/websockets/v3?app_id={self.config.DERIV_APP_ID}"
            logger.info(f"🔄 Conectando...")
            
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            self.running = True
            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
    
    def on_open(self, ws):
        logger.info("✅ Conectado")
        self.connected = True
        self.reconnect_attempts = 0
        self.authorize()
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            if 'authorize' in data:
                self.on_authorize(data)
            elif 'tick' in data:
                self.on_tick(data['tick'])
            elif 'balance' in data:
                self.on_balance(data['balance'])
            elif 'buy' in data:
                self.on_trade_result(data['buy'])
            elif 'cashier' in data:
                self.on_cashier_response(data['cashier'])
            elif 'transfer_between_accounts' in data:
                self.on_transfer_response(data['transfer_between_accounts'])
            elif 'payout_currencies' in data:
                self.on_payout_currencies(data['payout_currencies'])
            elif 'error' in data:
                logger.error(f"❌ Erro: {data['error']['message']}")
                
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
    
    def on_error(self, ws, error):
        logger.error(f"❌ WebSocket: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        logger.warning("🔌 Desconectado")
        self.connected = False
        self.authorized = False
        self.balance_subscribed = False
        
        if self.running:
            self.reconnect_attempts += 1
            wait_time = min(30, 5 * self.reconnect_attempts)
            logger.info(f"🔄 Reconectar em {wait_time}s...")
            time.sleep(wait_time)
            self.connect()
    
    def authorize(self):
        if not self.config.DERIV_API_TOKEN:
            logger.error("❌ Token não configurado")
            return
        
        auth_request = {"authorize": self.config.DERIV_API_TOKEN}
        self.ws.send(json.dumps(auth_request))
        logger.info("🔑 Autorizando...")
    
    def on_authorize(self, data):
        try:
            self.authorized = True
            self.balance = float(data['authorize']['balance'])
            self.currency = data['authorize']['currency']
            self.loginid = data['authorize']['loginid']
            
            logger.info(f"✅ Autorizado! Saldo: {self.balance} {self.currency}")
            
            self.subscribe_balance()
            self.subscribe_ticks()
            
        except Exception as e:
            logger.error(f"Erro: {e}")
    
    def subscribe_balance(self):
        if not self.authorized or self.balance_subscribed:
            return
        
        balance_request = {"balance": 1, "subscribe": 1}
        self.ws.send(json.dumps(balance_request))
        self.balance_subscribed = True
        logger.info("💰 Inscrito em atualizações de saldo")
    
    def on_balance(self, balance_data):
        try:
            self.balance = float(balance_data['balance'])
            self.currency = balance_data['currency']
            logger.info(f"💰 Saldo: {self.balance} {self.currency}")
        except Exception as e:
            logger.error(f"Erro: {e}")
    
    def subscribe_ticks(self, symbol=None):
        if symbol:
            self.current_symbol = symbol
        tick_request = {"ticks": self.current_symbol, "subscribe": 1}
        self.ws.send(json.dumps(tick_request))
        logger.info(f"📊 Subscrito a {self.current_symbol}")
    
    def on_tick(self, tick):
        try:
            tick_info = {
                'symbol': tick['symbol'],
                'price': float(tick['quote']),
                'time': datetime.fromtimestamp(tick['epoch']).strftime('%H:%M:%S')
            }
            
            if self.on_tick_callback:
                self.on_tick_callback(tick_info)
                
        except Exception as e:
            logger.error(f"Erro: {e}")
    
    def place_trade(self, contract_type, amount, duration=1, is_digit=False):
        """VERSÃO QUE FUNCIONA - TESTADA NA DERIV"""
        if not self.authorized:
            logger.error("❌ Não autorizado")
            return None
        
        try:
            # Para dígitos
            if is_digit:
                if contract_type == "CALL":
                    contract = "DIGITODD"
                else:
                    contract = "DIGITEVEN"
                duration_unit = "t"
                trade_duration = 1
            else:
                contract = contract_type
                duration_unit = "m"
                trade_duration = 1
            
            # Request no formato que FUNCIONOU
            trade_request = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": contract,
                    "currency": self.currency,
                    "duration": trade_duration,
                    "duration_unit": duration_unit,
                    "symbol": self.current_symbol
                }
            }
            
            # Adiciona markup se configurado
            if self.markup_percentage > 0:
                trade_request["parameters"]["app_markup_percentage"] = str(self.markup_percentage)
            
            logger.info(f"🎯 Enviando: {contract} ${amount}")
            self.ws.send(json.dumps(trade_request))
            return True
            
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None
    
    def on_trade_result(self, result):
        try:
            logger.info(f"📊 Resultado: {result}")
            
            if 'balance_after' in result:
                self.balance = float(result['balance_after'])
                logger.info(f"💰 Novo saldo: {self.balance}")
            
            if self.trading_bot and len(self.trading_bot.trades) > 0:
                is_win = result.get('sell_price', 0) > result.get('buy_price', 0)
                
                last_trade = self.trading_bot.trades[-1]
                last_trade['result'] = 'win' if is_win else 'loss'
                if is_win:
                    last_trade['profit'] = result.get('sell_price', 0) - result.get('buy_price', 0)
                
                self.trading_bot.update_stats()
                
        except Exception as e:
            logger.error(f"Erro: {e}")
    
    def on_cashier_response(self, cashier_data):
        try:
            logger.info(f"💰 Cashier response: {cashier_data}")
        except Exception as e:
            logger.error(f"Erro ao processar cashier: {e}")

    def on_transfer_response(self, transfer_data):
        try:
            logger.info(f"💸 Transfer response: {transfer_data}")
        except Exception as e:
            logger.error(f"Erro ao processar transferência: {e}")

    def on_payout_currencies(self, currencies_data):
        try:
            logger.info(f"💱 Moedas disponíveis: {currencies_data}")
        except Exception as e:
            logger.error(f"Erro ao processar moedas: {e}")
    
    def change_symbol(self, symbol):
        self.subscribe_ticks(symbol)
    
    def disconnect(self):
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("👋 Desconectado")
