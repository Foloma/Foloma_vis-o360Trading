import numpy as np
import logging
from indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

class TradingStrategy:
    """Estratégia multi-indicadores com pesos"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.signals_history = []
        
    def analyze_macd(self, macd, signal, hist):
        """Análise do MACD"""
        if macd is None or signal is None:
            return 0
            
        try:
            # MACD cruzando acima da linha de sinal (COMPRA)
            if macd > signal and hist > 0:
                return 1
            # MACD cruzando abaixo da linha de sinal (VENDA)
            elif macd < signal and hist < 0:
                return -1
            else:
                return 0
        except:
            return 0
    
    def analyze_rsi(self, rsi):
        """Análise do RSI"""
        if rsi is None:
            return 0
            
        try:
            # RSI sobrevendido (COMPRA)
            if rsi < 30:
                return 1
            # RSI sobrecomprado (VENDA)
            elif rsi > 70:
                return -1
            # Neutro
            elif 40 < rsi < 60:
                return 0.5 if rsi < 50 else -0.5
            else:
                return 0
        except:
            return 0
    
    def analyze_bollinger(self, price, upper, middle, lower):
        """Análise das Bandas de Bollinger"""
        if upper is None or lower is None or price is None:
            return 0
            
        try:
            # Preço abaixo da banda inferior (COMPRA)
            if price <= lower:
                return 1
            # Preço acima da banda superior (VENDA)
            elif price >= upper:
                return -1
            # Preço na média (neutro)
            elif middle is not None and abs(price - middle) / middle < 0.01:
                return 0
            # Preço entre as bandas
            elif price < middle:
                return 0.3  # Levemente comprador
            else:
                return -0.3  # Levemente vendedor
        except:
            return 0
    
    def analyze_moving_averages(self, sma9, sma21, sma50, price):
        """Análise de cruzamento de médias"""
        if sma9 is None or sma21 is None:
            return 0
            
        try:
            score = 0
            
            # Golden Cross (9 acima de 21) - COMPRA
            if sma9 > sma21:
                score += 0.5
            # Death Cross (9 abaixo de 21) - VENDA
            else:
                score -= 0.5
                
            # Preço acima das médias - COMPRA
            if price > sma9 and price > sma21:
                score += 0.5
            # Preço abaixo das médias - VENDA
            elif price < sma9 and price < sma21:
                score -= 0.5
                
            return score
        except:
            return 0
    
    def get_signal(self, price):
        """Obtém sinal consolidado baseado em todos os indicadores"""
        
        # Adiciona preço aos indicadores
        self.indicators.add_price(price)
        indicators = self.indicators.get_all_indicators()
        
        # Inicializa pontuações
        scores = {}
        
        # 1. MACD
        macd_signal = self.analyze_macd(
            indicators.get('MACD'),
            indicators.get('MACD_Signal'),
            indicators.get('MACD_Hist')
        )
        scores['MACD'] = macd_signal * 0.30
        
        # 2. RSI
        rsi_signal = self.analyze_rsi(indicators.get('RSI'))
        scores['RSI'] = rsi_signal * 0.25
        
        # 3. Bollinger Bands
        bb_signal = self.analyze_bollinger(
            price,
            indicators.get('BB_Upper'),
            indicators.get('BB_Middle'),
            indicators.get('BB_Lower')
        )
        scores['BB'] = bb_signal * 0.20
        
        # 4. Médias Móveis
        ma_signal = self.analyze_moving_averages(
            indicators.get('SMA_9'),
            indicators.get('SMA_21'),
            indicators.get('SMA_50'),
            price
        )
        scores['MA'] = ma_signal * 0.15
        
        # 5. Volume/ADX
        adx = indicators.get('ADX')
        adx_signal = 0.3 if adx and adx > 25 else -0.1
        scores['ADX'] = adx_signal * 0.10
        
        # Calcula pontuação total (entre -1 e 1)
        total_score = sum(scores.values())
        
        # Determina ação baseada na pontuação
        action = 'NEUTRAL'
        confidence = abs(total_score)
        
        if total_score > 0.25:
            action = 'BUY'
        elif total_score < -0.25:
            action = 'SELL'
            
        # Log detalhado
        signal_data = {
            'price': price,
            'action': action,
            'confidence': confidence,
            'total_score': total_score,
            'scores': scores,
            'indicators': indicators
        }
        
        self.signals_history.append(signal_data)
        
        return signal_data
    
    def should_enter_trade(self, signal):
        """Decide se deve entrar em um trade"""
        if signal['action'] == 'NEUTRAL':
            return False
            
        # Confirmação com ADX (força da tendência)
        adx = signal['indicators'].get('ADX')
        if adx and adx < 20 and signal['action'] != 'NEUTRAL':
            if signal['confidence'] < 0.5:
                return False
                
        # Confirmação com estocástico
        stoch = signal['indicators'].get('Stochastic')
        if stoch:
            if signal['action'] == 'BUY' and stoch > 80:
                return False
            elif signal['action'] == 'SELL' and stoch < 20:
                return False
                
        return True
