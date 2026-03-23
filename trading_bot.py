import logging
import time
from collections import deque
from datetime import datetime, timedelta
from indicators import TechnicalIndicators
from synthetics import digit_analyzer
from config import config

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.client = None
        self.indicators = TechnicalIndicators()
        self.current_price = 0
        self.current_symbol = 'R_100'
        self.balance = 0
        self.currency = 'USD'
        self.paused = False
        self.last_analysis = {}
        
        # Estatísticas detalhadas
        self.stats = {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'profit_loss': 0,
            'total_invested': 0,
            'total_return': 0
        }
        
        # Controle diário
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'profit_loss': 0,
            'start_balance': 0
        }
        
        # Histórico de trades
        self.trades = deque(maxlen=100)
        
        # Sistema de perdas consecutivas
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # Sistema Martingale
        self.martingale = {
            'active': False,
            'step': 0,
            'original_amount': 0,
            'last_result': None
        }
        
    def start(self, client):
        self.client = client
        self.daily_stats['start_balance'] = self.balance
        logger.info("🚀 Bot iniciado")
    
    def pause(self):
        self.paused = True
        logger.info("⏸️ Pausado")
    
    def resume(self):
        self.paused = False
        logger.info("▶️ Resumido")
    
    def on_tick(self, tick):
        self.current_price = tick['price']
        self.current_symbol = tick['symbol']
        self.indicators.add_price(self.current_price)
        
        if 'R_' in self.current_symbol:
            digit_analyzer.add_tick(self.current_price)
        
        self.last_analysis = self.indicators.get_all_indicators()
        
        if self.client:
            self.balance = self.client.balance
            self.currency = self.client.currency
            
            today = datetime.now().date()
            if self.daily_stats['date'] != today:
                self.reset_daily_stats()
    
    def reset_daily_stats(self):
        self.daily_stats = {
            'date': datetime.now().date(),
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'profit_loss': 0,
            'start_balance': self.balance
        }
        logger.info("📅 Estatísticas diárias resetadas")
    
    def calculate_signal(self):
        if not self.last_analysis:
            return 'NEUTRAL', 0
        
        analysis = self.last_analysis
        
        # NOVOS PESOS - MAIS ÊNFASE EM TENDÊNCIA E RSI
        weights = {
            'trend': 0.40,      # Aumentado de 0.35 para 0.40
            'rsi': 0.30,        # Aumentado de 0.25 para 0.30
            'macd': 0.15,       # Reduzido de 0.20 para 0.15
            'bollinger': 0.15   # Reduzido de 0.20 para 0.15
        }
        
        buy_score = 0
        sell_score = 0
        
        # TENDÊNCIA (40% do peso)
        if 'ALTA' in analysis['trend']['desc']:
            buy_score += analysis['trend']['score'] * weights['trend']
        elif 'BAIXA' in analysis['trend']['desc']:
            sell_score += analysis['trend']['score'] * weights['trend']
        
        # RSI (30% do peso)
        if 'SOBREVENDIDO' in analysis['rsi']['desc']:
            buy_score += (100 - analysis['rsi']['score']) * weights['rsi']
        elif 'SOBRECOMPRADO' in analysis['rsi']['desc']:
            sell_score += analysis['rsi']['score'] * weights['rsi']
        elif analysis['rsi']['score'] < 40:
            buy_score += (40 - analysis['rsi']['score']) * weights['rsi'] * 0.8
        elif analysis['rsi']['score'] > 60:
            sell_score += (analysis['rsi']['score'] - 60) * weights['rsi'] * 0.8
        
        # MACD (15% do peso)
        if 'COMPRA' in analysis['macd']['desc']:
            buy_score += analysis['macd']['score'] * weights['macd']
        elif 'VENDA' in analysis['macd']['desc']:
            sell_score += analysis['macd']['score'] * weights['macd']
        
        # BOLLINGER (15% do peso)
        if 'COMPRA' in analysis['bollinger']['desc']:
            buy_score += analysis['bollinger']['score'] * weights['bollinger']
        elif 'VENDA' in analysis['bollinger']['desc']:
            sell_score += analysis['bollinger']['score'] * weights['bollinger']
        
        total = buy_score + sell_score
        if total == 0:
            return 'NEUTRAL', 0
        
        if buy_score > sell_score:
            confidence = (buy_score / total) * 100
            return 'BUY', min(confidence, 98)
        else:
            confidence = (sell_score / total) * 100
            return 'SELL', min(confidence, 98)
    
    def confirm_signal(self, signal, confidence):
        """Confirma sinal com análise adicional"""
        if confidence < 75:
            return False, "Confiança insuficiente"
        
        analysis = self.last_analysis
        
        # Regra 1: Não operar contra a tendência forte
        if 'FORTE' in analysis['trend']['desc']:
            if signal == 'BUY' and 'BAIXA' in analysis['trend']['desc']:
                return False, "Contra tendência forte de BAIXA"
            if signal == 'SELL' and 'ALTA' in analysis['trend']['desc']:
                return False, "Contra tendência forte de ALTA"
        
        # Regra 2: Verificar RSI em extremos
        if signal == 'BUY' and analysis['rsi']['score'] > 70:
            return False, f"RSI sobrecomprado ({analysis['rsi']['score']:.1f}) - aguardar correção"
        
        if signal == 'SELL' and analysis['rsi']['score'] < 30:
            return False, f"RSI sobrevendido ({analysis['rsi']['score']:.1f}) - aguardar recuperação"
        
        # Regra 3: Verificar MACD
        if signal == 'BUY' and 'VENDA' in analysis['macd']['desc']:
            return False, "MACD indica VENDA"
        
        if signal == 'SELL' and 'COMPRA' in analysis['macd']['desc']:
            return False, "MACD indica COMPRA"
        
        return True, "Sinal confirmado"
    
    def get_max_stake(self):
        max_percent = config.RISK_LIMITS.get('max_stake_percent', 5)
        max_amount = (self.balance * max_percent) / 100
        return max(0.35, min(max_amount, config.MAX_STAKE))
    
    def get_recommended_stake(self, confidence):
        if self.balance <= 0:
            return config.DEFAULT_STAKE
        
        base_percent = {
            90: 5, 80: 3, 70: 2, 60: 1
        }
        
        for threshold, percent in base_percent.items():
            if confidence >= threshold:
                amount = (self.balance * percent) / 100
                return max(0.35, min(amount, config.MAX_STAKE))
        
        return config.DEFAULT_STAKE
    
    def get_martingale_amount(self, base_amount):
        if not self.martingale['active'] or self.martingale['step'] == 0:
            return base_amount
        
        multiplier = config.MARTINGALE_CONFIG.get('multiplier', 2.0)
        step = self.martingale['step']
        martingale_amount = base_amount * (multiplier ** step)
        
        max_stake = self.get_max_stake()
        if martingale_amount > max_stake:
            martingale_amount = max_stake
        
        return martingale_amount
    
    def apply_martingale_after_loss(self, last_trade_amount):
        if not config.MARTINGALE_CONFIG.get('enabled', True):
            return False, "Martingale desativado"
        
        max_steps = config.MARTINGALE_CONFIG.get('max_steps', 2)
        
        if self.martingale['step'] >= max_steps:
            return False, f"Máximo de {max_steps} perdas consecutivas atingido"
        
        self.martingale['step'] += 1
        self.martingale['active'] = True
        self.martingale['original_amount'] = last_trade_amount
        
        next_amount = self.get_martingale_amount(last_trade_amount)
        
        return True, {
            'step': self.martingale['step'],
            'next_amount': next_amount,
            'multiplier': config.MARTINGALE_CONFIG.get('multiplier', 2.0),
            'message': f"📈 Martingale ativo - Passo {self.martingale['step']}/{max_steps} | Próximo valor: ${next_amount:.2f}"
        }
    
    def reset_martingale(self):
        self.martingale = {
            'active': False,
            'step': 0,
            'original_amount': 0,
            'last_result': None
        }
        logger.info("🔄 Martingale resetado")
    
    def get_martingale_status(self):
        return {
            'active': self.martingale['active'],
            'step': self.martingale['step'],
            'original_amount': self.martingale['original_amount'],
            'next_amount': self.get_martingale_amount(config.DEFAULT_STAKE),
            'max_steps': config.MARTINGALE_CONFIG.get('max_steps', 2),
            'multiplier': config.MARTINGALE_CONFIG.get('multiplier', 2.0),
            'enabled': config.MARTINGALE_CONFIG.get('enabled', True)
        }
    
    def check_risk_limits(self):
        today = datetime.now().date()
        
        if self.daily_stats['profit_loss'] < 0:
            loss_percent = abs(self.daily_stats['profit_loss'] / self.daily_stats['start_balance']) * 100
            max_loss_percent = config.RISK_LIMITS.get('max_daily_loss_percent', 5)
            if loss_percent >= max_loss_percent:
                return False, f"Limite diário de perdas atingido: {loss_percent:.1f}%"
        
        if config.RISK_LIMITS.get('take_profit_enabled', True):
            profit_percent = (self.daily_stats['profit_loss'] / self.daily_stats['start_balance']) * 100
            daily_target = config.RISK_LIMITS.get('daily_target_percent', 10)
            if profit_percent >= daily_target:
                return False, f"Meta diária atingida: {profit_percent:.1f}%"
        
        max_consecutive = config.RISK_LIMITS.get('max_consecutive_losses', 2)
        if self.consecutive_losses >= max_consecutive:
            return False, f"Máximo de {max_consecutive} perdas consecutivas atingido"
        
        return True, "OK"
    
    def can_trade(self, confidence):
        if not self.client or not self.client.authorized:
            return False, "Não conectado"
        if self.paused:
            return False, "Bot pausado"
        
        min_confidence = config.RISK_LIMITS.get('min_confidence', 75)
        if confidence < min_confidence:
            return False, f"Confiança baixa: {confidence:.1f}% (mínimo {min_confidence}%)"
        
        risk_ok, risk_msg = self.check_risk_limits()
        if not risk_ok:
            return False, risk_msg
        
        return True, "OK"
    
    def register_trade(self, trade_data):
        trade_data['timestamp'] = datetime.now()
        self.trades.append(trade_data)
        self.stats['total'] += 1
        self.stats['total_invested'] += trade_data['amount']
        self.daily_stats['trades'] += 1
        
        self.update_stats()
    
    def update_stats(self):
        wins = 0
        losses = 0
        profit_loss = 0
        
        for trade in self.trades:
            if trade.get('result') == 'win':
                wins += 1
                profit_loss += trade.get('profit', 0)
            elif trade.get('result') == 'loss':
                losses += 1
                profit_loss -= trade.get('amount', 0)
        
        self.stats['wins'] = wins
        self.stats['losses'] = losses
        self.stats['win_rate'] = (wins / self.stats['total']) * 100 if self.stats['total'] > 0 else 0
        self.stats['profit_loss'] = profit_loss
        self.stats['total_return'] = (profit_loss / self.stats['total_invested']) * 100 if self.stats['total_invested'] > 0 else 0
    
    def get_trade_report(self):
        hoje = datetime.now().date()
        trades_hoje = [t for t in self.trades if t['timestamp'].date() == hoje]
        
        maior_ganho = 0
        maior_perda = 0
        for trade in self.trades:
            if trade.get('result') == 'win':
                maior_ganho = max(maior_ganho, trade.get('profit', 0))
            elif trade.get('result') == 'loss':
                maior_perda = max(maior_perda, trade.get('amount', 0))
        
        sequencia = {'tipo': 'N/A', 'tamanho': 0}
        if len(self.trades) > 0:
            ultimo = self.trades[-1]
            tipo = 'win' if ultimo.get('result') == 'win' else 'loss'
            count = 1
            for i in range(len(self.trades)-2, -1, -1):
                if self.trades[i].get('result') == tipo:
                    count += 1
                else:
                    break
            sequencia = {'tipo': tipo, 'tamanho': count}
        
        return {
            'resumo': {
                'total_trades': self.stats['total'],
                'trades_hoje': len(trades_hoje),
                'wins': self.stats['wins'],
                'losses': self.stats['losses'],
                'win_rate': round(self.stats['win_rate'], 2),
                'profit_loss': round(self.stats['profit_loss'], 2),
                'maior_ganho': round(maior_ganho, 2),
                'maior_perda': round(maior_perda, 2),
                'sequencia_atual': sequencia,
                'total_invested': round(self.stats['total_invested'], 2),
                'total_return': round(self.stats['total_return'], 2)
            },
            'historico': [{
                'time': t['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': t.get('symbol', ''),
                'action': t.get('action', ''),
                'amount': t.get('amount', 0),
                'result': t.get('result', 'pending'),
                'profit': t.get('profit', 0)
            } for t in list(self.trades)[-50:]]
        }
    
    def get_status(self):
        signal, confidence = self.calculate_signal()
        
        return {
            'connected': self.client.connected if self.client else False,
            'authorized': self.client.authorized if self.client else False,
            'price': self.current_price,
            'symbol': self.current_symbol,
            'balance': self.balance,
            'currency': self.currency,
            'signal': signal,
            'confidence': round(confidence, 1),
            'analysis': self.last_analysis,
            'stats': self.stats,
            'paused': self.paused,
            'martingale': self.get_martingale_status(),
            'daily_stats': self.daily_stats
        }

trading_bot = TradingBot()
