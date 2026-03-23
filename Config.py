import os
from dotenv import load_dotenv
import logging

load_dotenv()

class Config:
    # Deriv API
    DERIV_APP_ID = os.getenv('DERIV_APP_ID', '1089')
    
    # Tokens (guardados no servidor, não partilhados)
    DEMO_API_TOKEN = os.getenv('DEMO_API_TOKEN', '')
    REAL_API_TOKEN = os.getenv('REAL_API_TOKEN', '')
    
    # WebSocket
    WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"
    
    # Tipos de conta
    ACCOUNT_TYPES = {
        'demo': {'name': 'Conta Demo', 'token': DEMO_API_TOKEN, 'is_virtual': 1},
        'real': {'name': 'Conta Real', 'token': REAL_API_TOKEN, 'is_virtual': 0}
    }
    
    # Símbolos disponíveis
    AVAILABLE_SYMBOLS = {
        'R_100': 'Volatility 100',
        'R_75': 'Volatility 75',
        'R_50': 'Volatility 50'
    }
    
    # Configurações de trading
    DEFAULT_STAKE = 0.35
    MIN_STAKE = 0.35
    MAX_STAKE = 100
    
    # Markup para conta REAL (ganhas comissão)
    MARKUP_PERCENTAGE = 0.5  # 0.5% em cada trade
    
    # Configurações de MARTINGALE
    MARTINGALE_CONFIG = {
        'enabled': True,
        'multiplier': 2.0,
        'max_steps': 2,
        'reset_on_win': True
    }
    
    # NOVO: Configurações de RISK LIMITS (adicionado para corrigir o erro)
    RISK_LIMITS = {
        'max_daily_loss_percent': 5,      # Máximo 5% da banca por dia
        'max_consecutive_losses': 2,      # Máximo 2 perdas consecutivas
        'min_confidence': 70,             # Confiança mínima para entrada (70%)
        'max_stake_percent': 5,           # Máximo 5% da banca por trade
        'stop_loss_enabled': True,        # Stop-loss ativo
        'take_profit_enabled': True,      # Take-profit ativo
        'daily_target_percent': 10        # Meta diária de 10%
    }
    
    LOG_LEVEL = logging.INFO

config = Config()
