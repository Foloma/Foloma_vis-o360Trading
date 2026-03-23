from flask import Flask, render_template, jsonify, request, session, redirect
import threading
import time
import logging
import hashlib
import base64
import json
import os
from collections import deque
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from config import config
from deriv_client import DerivWebSocketClient
from trading_bot import trading_bot
from synthetics import digit_analyzer
from payment_system import PaymentSystem

app = Flask(__name__)
app.secret_key = 'foloma_trading_secret_key_2024'

deriv_client = None
payment_system = None

# ========== SISTEMA DE UTILIZADORES ==========
# Em produção, usar banco de dados (SQLite, PostgreSQL, etc.)
# Para teste, usamos um arquivo JSON
USERS_FILE = 'users.json'

def load_users():
    """Carrega utilizadores do arquivo"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Guarda utilizadores no arquivo"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# Carrega utilizadores existentes
users = load_users()

# ========== SISTEMA DE AFILIADO ==========
class AffiliateSystem:
    def __init__(self):
        self.referrals = deque(maxlen=1000)
        self.commissions = {
            'total': 0,
            'pending': 0,
            'paid': 0,
            'history': deque(maxlen=100)
        }
        
    def generate_referral_link(self, user_id):
        code = base64.b64encode(hashlib.md5(str(user_id).encode()).digest())[:8].decode()
        return f"https://foloma.com/ref/{code}"
    
    def track_referral(self, referrer_id, new_user_id):
        referral = {
            'referrer_id': referrer_id,
            'new_user_id': new_user_id,
            'timestamp': time.time(),
            'status': 'pending',
            'commission': 0
        }
        self.referrals.append(referral)
        logger.info(f"📢 Nova indicação: {referrer_id} -> {new_user_id}")
        return referral
    
    def calculate_commission(self, trade_amount, markup_percentage):
        commission = trade_amount * (markup_percentage / 100)
        self.commissions['total'] += commission
        self.commissions['pending'] += commission
        return commission
    
    def get_affiliate_stats(self):
        return {
            'total_referrals': len(self.referrals),
            'total_commission': round(self.commissions['total'], 2),
            'pending_commission': round(self.commissions['pending'], 2),
            'paid_commission': round(self.commissions['paid'], 2)
        }

affiliate = AffiliateSystem()

# ========== FUNÇÕES AUXILIARES ==========
def on_tick_callback(tick):
    trading_bot.on_tick(tick)

def require_auth(f):
    """Decorator para verificar autenticação"""
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# ========== ROTAS DE AUTENTICAÇÃO ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/auth/status')
def api_auth_status():
    """Verifica se o utilizador está autenticado"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'name': session.get('user_name'),
                'email': session.get('user_email')
            }
        })
    return jsonify({'authenticated': False})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Regista um novo utilizador"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        referral_code = data.get('referral_code', '')
        
        # Validações
        if not name or not email or not password:
            return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'A senha deve ter pelo menos 6 caracteres'}), 400
        
        if email in users:
            return jsonify({'error': 'Email já registado'}), 400
        
        # Cria novo utilizador
        user_id = str(int(time.time() * 1000))  # ID único baseado no timestamp
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        users[email] = {
            'id': user_id,
            'name': name,
            'email': email,
            'password': password_hash,
            'deriv_token': None,
            'deriv_account_type': None,
            'created_at': time.time(),
            'last_login': None,
            'referral_code': referral_code,
            'referrals': []
        }
        
        save_users(users)
        
        # Processa indicação se houver
        if referral_code:
            for u_email, u_data in users.items():
                if u_data.get('referral_link_code') == referral_code:
                    affiliate.track_referral(u_data['id'], user_id)
                    break
        
        logger.info(f"📝 Novo utilizador: {email}")
        
        return jsonify({
            'status': 'ok',
            'message': 'Conta criada com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro no registo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login do utilizador"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        user = users.get(email)
        if not user:
            return jsonify({'error': 'Utilizador não encontrado'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user['password'] != password_hash:
            return jsonify({'error': 'Senha incorreta'}), 400
        
        # Atualiza último login
        users[email]['last_login'] = time.time()
        save_users(users)
        
        # Cria sessão
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        
        logger.info(f"🔐 Login: {email}")
        
        return jsonify({
            'status': 'ok',
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'has_deriv_token': bool(user.get('deriv_token'))
            }
        })
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Logout do utilizador"""
    session.clear()
    return jsonify({'status': 'ok'})

@app.route('/api/auth/user')
@require_auth
def api_get_user():
    """Retorna dados do utilizador autenticado"""
    email = session.get('user_email')
    user = users.get(email)
    
    if not user:
        return jsonify({'error': 'Utilizador não encontrado'}), 404
    
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'has_deriv_token': bool(user.get('deriv_token')),
            'deriv_account_type': user.get('deriv_account_type'),
            'created_at': user['created_at']
        }
    })

@app.route('/api/auth/save_token', methods=['POST'])
@require_auth
def api_save_token():
    """Guarda o token da Deriv do utilizador"""
    try:
        data = request.json
        token = data.get('token')
        account_type = data.get('account_type', 'demo')
        
        if not token:
            return jsonify({'error': 'Token necessário'}), 400
        
        email = session.get('user_email')
        if email not in users:
            return jsonify({'error': 'Utilizador não encontrado'}), 404
        
        users[email]['deriv_token'] = token
        users[email]['deriv_account_type'] = account_type
        save_users(users)
        
        logger.info(f"💾 Token guardado para {email}")
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Erro ao guardar token: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/delete_token', methods=['POST'])
@require_auth
def api_delete_token():
    """Remove o token da Deriv do utilizador"""
    try:
        email = session.get('user_email')
        if email in users:
            users[email]['deriv_token'] = None
            users[email]['deriv_account_type'] = None
            save_users(users)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/generate_referral_link', methods=['GET'])
@require_auth
def api_generate_referral_link():
    """Gera link de indicação para o utilizador"""
    try:
        user_id = session.get('user_id')
        email = session.get('user_email')
        
        # Gera código único
        code = base64.b64encode(hashlib.md5(str(user_id).encode()).digest())[:8].decode()
        
        # Guarda código no perfil do utilizador
        if email in users:
            users[email]['referral_link_code'] = code
            save_users(users)
        
        link = f"https://foloma.com/?ref={code}"
        
        return jsonify({'link': link, 'code': code})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ROTAS DA PLATAFORMA ==========

@app.route('/api/connect', methods=['POST'])
@require_auth
def api_connect():
    """Conecta à Deriv com o token do utilizador"""
    global deriv_client, payment_system
    
    try:
        data = request.json
        account_type = data.get('account_type', 'demo')
        symbol = data.get('symbol', 'R_100')
        
        email = session.get('user_email')
        user = users.get(email)
        
        if not user:
            return jsonify({'error': 'Utilizador não encontrado'}), 404
        
        token = user.get('deriv_token')
        if not token:
            return jsonify({'error': 'Token não configurado. Configure o token nas definições.'}), 400
        
        logger.info(f"🔌 Conectando à conta {account_type.upper()} para {email}")
        config.DERIV_API_TOKEN = token
        
        deriv_client = DerivWebSocketClient(config, on_tick_callback)
        deriv_client.set_trading_bot(trading_bot)
        
        if account_type == 'real':
            deriv_client.markup_percentage = config.MARKUP_PERCENTAGE
            logger.info(f"💰 Markup ativo: {config.MARKUP_PERCENTAGE}%")
        
        deriv_client.connect()
        
        time.sleep(2)
        deriv_client.subscribe_ticks(symbol)
        
        trading_bot.start(deriv_client)
        
        payment_system = PaymentSystem(deriv_client)
        deriv_client.set_payment_system(payment_system)
        
        return jsonify({
            'status': 'conectando',
            'account_type': account_type,
            'is_demo': account_type == 'demo'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
@require_auth
def api_status():
    """Status da plataforma"""
    try:
        if deriv_client:
            trading_bot.balance = deriv_client.balance
            trading_bot.currency = deriv_client.currency
        
        status = trading_bot.get_status()
        
        return jsonify({
            'bot': status,
            'digits': {
                'last': digit_analyzer.get_current_digit(),
                'parity': digit_analyzer.get_current_parity(),
                'stats': digit_analyzer.get_stats(),
                'analysis': digit_analyzer.get_analysis(),
                'recent': digit_analyzer.get_recent_digits(20)
            },
            'symbols': config.AVAILABLE_SYMBOLS
        })
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbol/change', methods=['POST'])
@require_auth
def api_symbol_change():
    try:
        data = request.json
        symbol = data.get('symbol')
        
        if symbol not in config.AVAILABLE_SYMBOLS:
            return jsonify({'error': 'Símbolo inválido'}), 400
        
        if deriv_client:
            deriv_client.change_symbol(symbol)
            trading_bot.current_symbol = symbol
            
        return jsonify({'status': 'ok', 'symbol': symbol})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade', methods=['POST'])
@require_auth
def api_trade():
    try:
        data = request.json
        action = data.get('action')
        amount = float(data.get('amount', 0.35))
        
        if not deriv_client or not deriv_client.authorized:
            return jsonify({'error': 'Não conectado'}), 400
        
        if amount < 0.35 or amount > 100:
            return jsonify({'error': 'Valor inválido'}), 400
        
        signal, confidence = trading_bot.calculate_signal()
        
        min_confidence = config.RISK_LIMITS.get('min_confidence', 70)
        if confidence < min_confidence:
            return jsonify({'error': f'Confiança baixa: {confidence:.1f}% (mínimo {min_confidence}%)'}), 400
        
        contract_type = 'CALL' if action == 'BUY' else 'PUT'
        
        success = deriv_client.place_trade(
            contract_type=contract_type,
            amount=amount,
            is_digit=False
        )
        
        if success:
            trade_data = {
                'symbol': trading_bot.current_symbol,
                'action': action,
                'amount': amount,
                'price': trading_bot.current_price,
                'result': 'pending',
                'confidence': confidence
            }
            trading_bot.register_trade(trade_data)
            
            # Calcula comissão para afiliado
            if hasattr(deriv_client, 'markup_percentage') and deriv_client.markup_percentage > 0:
                commission = affiliate.calculate_commission(amount, deriv_client.markup_percentage)
                logger.info(f"💰 Comissão gerada: ${commission:.2f}")
            
            return jsonify({
                'status': 'ok', 
                'message': f'Trade {action} enviado',
                'confidence': confidence
            })
        else:
            return jsonify({'error': 'Falha no trade'}), 500
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trade/digit', methods=['POST'])
@require_auth
def api_trade_digit():
    try:
        data = request.json
        prediction = data.get('prediction')
        amount = float(data.get('amount', 0.35))
        
        if not deriv_client or not deriv_client.authorized:
            return jsonify({'error': 'Não conectado'}), 400
        
        if amount < 0.35 or amount > 100:
            return jsonify({'error': 'Valor inválido'}), 400
        
        analysis = digit_analyzer.get_analysis()
        confidence = analysis.get('confidence', 0)
        
        warning = None
        min_confidence = config.RISK_LIMITS.get('min_confidence', 70)
        if confidence < min_confidence:
            warning = f"Confiança baixa: {confidence}% (mínimo recomendado {min_confidence}%)"
        
        contract_type = 'CALL' if prediction == 'odd' else 'PUT'
        
        success = deriv_client.place_trade(
            contract_type=contract_type,
            amount=amount,
            is_digit=True
        )
        
        if success:
            trade_data = {
                'symbol': trading_bot.current_symbol,
                'action': 'DIGIT_' + ('ODD' if prediction == 'odd' else 'EVEN'),
                'amount': amount,
                'price': trading_bot.current_price,
                'result': 'pending',
                'confidence': confidence
            }
            trading_bot.register_trade(trade_data)
            
            response = {
                'status': 'ok', 
                'message': f'✅ Aposta em {prediction.upper()} executada!',
                'confidence': confidence
            }
            if warning:
                response['warning'] = warning
            
            # Calcula comissão para afiliado
            if hasattr(deriv_client, 'markup_percentage') and deriv_client.markup_percentage > 0:
                commission = affiliate.calculate_commission(amount, deriv_client.markup_percentage)
                logger.info(f"💰 Comissão gerada: ${commission:.2f}")
            
            return jsonify(response)
        else:
            return jsonify({'error': 'Falha no trade'}), 500
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/report')
@require_auth
def api_report():
    try:
        report = trading_bot.get_trade_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pause', methods=['POST'])
@require_auth
def api_pause():
    data = request.json
    paused = data.get('paused', True)
    
    if paused:
        trading_bot.pause()
    else:
        trading_bot.resume()
    
    return jsonify({'paused': paused})

@app.route('/api/martingale/status', methods=['GET'])
@require_auth
def api_martingale_status():
    try:
        status = trading_bot.get_martingale_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/martingale/apply', methods=['POST'])
@require_auth
def api_martingale_apply():
    try:
        data = request.json
        last_amount = float(data.get('last_amount', 0))
        
        if last_amount <= 0:
            return jsonify({'error': 'Valor do último trade inválido'}), 400
        
        success, result = trading_bot.apply_martingale_after_loss(last_amount)
        
        if success:
            return jsonify({
                'status': 'ok',
                'martingale': result
            })
        else:
            return jsonify({'error': result}), 400
        
    except Exception as e:
        logger.error(f"Erro no Martingale: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/martingale/reset', methods=['POST'])
@require_auth
def api_martingale_reset():
    try:
        trading_bot.reset_martingale()
        return jsonify({'status': 'ok', 'message': 'Martingale resetado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/affiliate/stats')
@require_auth
def api_affiliate_stats():
    try:
        stats = affiliate.get_affiliate_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/affiliate/link')
@require_auth
def api_affiliate_link():
    try:
        user_id = session.get('user_id')
        link = affiliate.generate_referral_link(user_id)
        return jsonify({'link': link, 'code': link.split('/')[-1]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== MAIN ==========

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🚀 FOLOMA TRADING - VERSÃO COMPLETA")
    logger.info("📍 http://127.0.0.1:5000")
    logger.info("="*60)
    logger.info("👥 Sistema de utilizadores: ATIVO")
    log
