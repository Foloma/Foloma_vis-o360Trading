from collections import deque
import time
import logging
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

class DigitAnalyzer:
    """Analisador de dígitos com detecção de padrões em tempo real"""
    
    def __init__(self, max_digits=20, analysis_interval=10):
        self.digits = deque(maxlen=100)
        self.timestamps = deque(maxlen=100)
        self.max_display = max_digits
        self.analysis_interval = analysis_interval  # 10 segundos entre análises
        self.last_analysis = time.time()
        self.current_digit = None
        self.current_parity = '---'
        self.countdown = analysis_interval
        self.analysis_in_progress = False
        
        # Dados da última análise
        self.last_analysis_data = {
            'streak': 0,
            'streak_parity': '---',
            'recommended_action': None,
            'confidence': 0,
            'pattern': 'Aguardando análise...',
            'alert': None,
            'reason': 'Aguardando dados...',
            'countdown': analysis_interval,
            'odd_pct': 0,
            'even_pct': 0,
            'recent_parity': []  # NOVO: últimos 20 dígitos com paridade
        }
        
        # Histórico de padrões detectados
        self.pattern_history = deque(maxlen=10)
        
        # Thread para contagem regressiva
        self.countdown_thread_running = True
        self.start_countdown_thread()
        
    def start_countdown_thread(self):
        """Inicia thread para atualizar contagem regressiva"""
        def update_countdown():
            while self.countdown_thread_running:
                time.sleep(1)
                if not self.analysis_in_progress:
                    elapsed = time.time() - self.last_analysis
                    self.countdown = max(0, self.analysis_interval - int(elapsed))
                    self.last_analysis_data['countdown'] = self.countdown
                    
                    # Quando chegar a 0, faz nova análise
                    if self.countdown <= 0 and not self.analysis_in_progress:
                        self.trigger_analysis()
                        
        thread = threading.Thread(target=update_countdown, daemon=True)
        thread.start()
    
    def add_tick(self, price):
        """Adiciona tick ao histórico e atualiza estatísticas em tempo real"""
        try:
            price_str = f"{price:.2f}"
            last_digit = int(price_str[-1])
            parity = 'IMPAR' if last_digit % 2 != 0 else 'PAR'
            
            self.digits.append(last_digit)
            self.timestamps.append(datetime.now())
            
            # Atualiza o dígito atual
            self.current_digit = last_digit
            self.current_parity = parity
            
            return True, self.current_digit
            
        except Exception as e:
            logger.error(f"Erro ao processar tick: {e}")
            return False, None
    
    def get_recent_parity_sequence(self):
        """Retorna a sequência de paridades dos últimos 20 dígitos"""
        recent = list(self.digits)[-20:]
        return ['IMPAR' if d % 2 != 0 else 'PAR' for d in recent]
    
    def get_streak_info(self):
        """Calcula a sequência atual de dígitos consecutivos"""
        if len(self.digits) < 2:
            return 0, '---'
        
        current_streak = 1
        last_parity = 'IMPAR' if self.digits[-1] % 2 != 0 else 'PAR'
        
        for i in range(len(self.digits)-2, -1, -1):
            parity = 'IMPAR' if self.digits[i] % 2 != 0 else 'PAR'
            if parity == last_parity:
                current_streak += 1
            else:
                break
        
        return current_streak, last_parity
    
    def analyze_trend(self):
        """Analisa a tendência dos últimos dígitos"""
        recent = list(self.digits)[-20:]
        if len(recent) < 10:
            return None
        
        odd_count = sum(1 for d in recent if d % 2 != 0)
        even_count = 20 - odd_count
        odd_pct = (odd_count / 20) * 100
        even_pct = (even_count / 20) * 100
        
        # Detecta tendência
        if odd_pct >= 65:
            return {
                'trend': 'IMPAR',
                'strength': odd_pct,
                'message': f'Fortemente tendendo para ÍMPAR ({odd_pct:.0f}%)'
            }
        elif even_pct >= 65:
            return {
                'trend': 'PAR',
                'strength': even_pct,
                'message': f'Fortemente tendendo para PAR ({even_pct:.0f}%)'
            }
        elif odd_pct >= 55:
            return {
                'trend': 'IMPAR',
                'strength': odd_pct,
                'message': f'Levemente tendendo para ÍMPAR ({odd_pct:.0f}%)'
            }
        elif even_pct >= 55:
            return {
                'trend': 'PAR',
                'strength': even_pct,
                'message': f'Levemente tendendo para PAR ({even_pct:.0f}%)'
            }
        else:
            return {
                'trend': 'NEUTRO',
                'strength': 50,
                'message': f'Sem tendência clara ({odd_pct:.0f}% ÍMPAR / {even_pct:.0f}% PAR)'
            }
    
    def trigger_analysis(self):
        """Dispara uma nova análise"""
        if self.analysis_in_progress:
            return
        
        self.analysis_in_progress = True
        self.last_analysis = time.time()
        
        try:
            analysis = self._perform_analysis()
            self.last_analysis_data = analysis
            self.last_analysis_data['countdown'] = self.analysis_interval
            logger.info(f"📊 ANÁLISE COMPLETADA: {analysis}")
            
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
        
        self.analysis_in_progress = False
    
    def _perform_analysis(self):
        """Realiza a análise completa dos dígitos"""
        if len(self.digits) < 10:
            return {
                'streak': 0,
                'streak_parity': '---',
                'recommended_action': None,
                'confidence': 0,
                'pattern': 'Acumulando dados...',
                'alert': None,
                'reason': f'Aguardando mais dados ({len(self.digits)}/10)',
                'odd_pct': 0,
                'even_pct': 0,
                'recent_parity': [],
                'trend_analysis': None,
                'countdown': self.analysis_interval
            }
        
        # Dados básicos
        recent_parity = self.get_recent_parity_sequence()
        streak, streak_parity = self.get_streak_info()
        trend = self.analyze_trend()
        
        # Estatísticas dos últimos 20 dígitos
        last_20 = list(self.digits)[-20:]
        odd_count = sum(1 for d in last_20 if d % 2 != 0)
        even_count = 20 - odd_count
        odd_pct = round((odd_count / 20) * 100, 1)
        even_pct = round((even_count / 20) * 100, 1)
        
        # Análise da sequência atual
        recommended_action = None
        confidence = 0
        alert = None
        reason = ''
        pattern_desc = ''
        
        # REGRA 1: Sequência de 3 ou mais PARES
        if streak >= 3 and streak_parity == 'PAR':
            confidence = min(65 + (streak - 3) * 10, 95)
            recommended_action = 'BUY'  # BUY = ÍMPAR
            alert = 'RECOMENDADO'
            reason = f'⚠️ {streak} PARES consecutivos! Próximo provavelmente ÍMPAR'
            pattern_desc = f'{streak} PARES consecutivos'
            
        # REGRA 2: Sequência de 3 ou mais ÍMPARES
        elif streak >= 3 and streak_parity == 'IMPAR':
            confidence = min(65 + (streak - 3) * 10, 95)
            recommended_action = 'SELL'  # SELL = PAR
            alert = 'RECOMENDADO'
            reason = f'⚠️ {streak} ÍMPARES consecutivos! Próximo provavelmente PAR'
            pattern_desc = f'{streak} ÍMPARES consecutivos'
            
        # REGRA 3: Tendência forte baseada nos últimos 20
        elif trend and trend['strength'] >= 65:
            confidence = 70
            if trend['trend'] == 'IMPAR':
                recommended_action = 'BUY'
                alert = 'SUGESTÃO'
                reason = trend['message']
                pattern_desc = f'Tendência para ÍMPAR ({trend["strength"]:.0f}%)'
            else:
                recommended_action = 'SELL'
                alert = 'SUGESTÃO'
                reason = trend['message']
                pattern_desc = f'Tendência para PAR ({trend["strength"]:.0f}%)'
                
        # REGRA 4: Tendência leve
        elif trend and trend['strength'] >= 55:
            confidence = 60
            if trend['trend'] == 'IMPAR':
                recommended_action = 'BUY'
                alert = 'LEVE'
                reason = trend['message']
                pattern_desc = f'Leve tendência para ÍMPAR'
            elif trend['trend'] == 'PAR':
                recommended_action = 'SELL'
                alert = 'LEVE'
                reason = trend['message']
                pattern_desc = f'Leve tendência para PAR'
            else:
                recommended_action = None
                alert = 'NEUTRO'
                reason = trend['message']
                pattern_desc = 'Sem tendência clara'
                
        else:
            alert = 'NEUTRO'
            reason = f'📊 Últimos 20: {odd_pct}% ÍMPAR / {even_pct}% PAR → Sem tendência clara'
            pattern_desc = 'Sem padrão claro'
        
        # Dados para exibição na interface
        return {
            'streak': streak,
            'streak_parity': streak_parity,
            'recommended_action': recommended_action,
            'confidence': confidence,
            'pattern': pattern_desc,
            'alert': alert,
            'reason': reason,
            'odd_pct': odd_pct,
            'even_pct': even_pct,
            'last_digit': self.current_digit,
            'last_parity': self.current_parity,
            'recent_parity': recent_parity[-20:],
            'trend_analysis': trend,
            'countdown': self.analysis_interval
        }
    
    def get_current_digit(self):
        return self.current_digit
    
    def get_current_parity(self):
        return self.current_parity
    
    def get_recent_digits(self, count=20):
        return list(self.digits)[-count:] if self.digits else []
    
    def get_analysis(self):
        """Retorna a última análise realizada"""
        return self.last_analysis_data
    
    def get_stats(self):
        """Estatísticas dos dígitos"""
        if not self.digits or len(self.digits) == 0:
            return {
                'total': 0,
                'odd_pct': 0,
                'even_pct': 0,
                'current_streak': 0,
                'streak_parity': '---',
                'recent': []
            }
        
        total = len(self.digits)
        odd_count = sum(1 for d in self.digits if d % 2 != 0)
        even_count = total - odd_count
        
        current_streak, streak_parity = self.get_streak_info()
        
        return {
            'total': total,
            'odd_pct': round((odd_count / total) * 100, 1),
            'even_pct': round((even_count / total) * 100, 1),
            'current_streak': current_streak,
            'streak_parity': streak_parity,
            'recent': self.get_recent_digits(20)
        }

digit_analyzer = DigitAnalyzer(max_digits=20, analysis_interval=10)
