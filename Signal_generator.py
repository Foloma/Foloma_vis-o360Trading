import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
import logging
from datetime import datetime, timedelta
import math
import json
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalGenerator:
    """
    Gerador de Sinais Avançado para Trading
    Utiliza múltiplos indicadores técnicos para gerar sinais precisos
    """
    
    def __init__(self):
        # Pesos dos indicadores na decisão final
        self.indicator_weights = {
            'moving_averages': 0.25,      # Médias Móveis
            'rsi': 0.15,                   # RSI
            'macd': 0.20,                   # MACD
            'bollinger': 0.15,               # Bandas de Bollinger
            'stochastic': 0.10,               # Estocástico
            'volume': 0.10,                   # Volume
            'trend': 0.05                      # Tendência
        }
        
        # Limiares para força do sinal
        self.signal_thresholds = {
            'strong_buy': 75,
            'buy': 60,
            'neutral': 40,
            'sell': 25,
            'strong_sell': 10
        }
        
        # Ativos disponíveis para análise
        self.assets = [
            {'symbol': 'R_100', 'name': 'Volatility 100 Index', 'type': 'synthetic'},
            {'symbol': 'R_75', 'name': 'Volatility 75 Index', 'type': 'synthetic'},
            {'symbol': 'R_50', 'name': 'Volatility 50 Index', 'type': 'synthetic'},
            {'symbol': 'R_25', 'name': 'Volatility 25 Index', 'type': 'synthetic'},
            {'symbol': 'R_10', 'name': 'Volatility 10 Index', 'type': 'synthetic'},
            {'symbol': '1HZ10V', 'name': 'Step Index 10', 'type': 'synthetic'},
            {'symbol': '1HZ25V', 'name': 'Step Index 25', 'type': 'synthetic'},
            {'symbol': '1HZ50V', 'name': 'Step Index 50', 'type': 'synthetic'},
            {'symbol': '1HZ75V', 'name': 'Step Index 75', 'type': 'synthetic'},
            {'symbol': '1HZ100V', 'name': 'Step Index 100', 'type': 'synthetic'},
            {'symbol': 'EURUSD', 'name': 'EUR/USD', 'type': 'forex'},
            {'symbol': 'GBPUSD', 'name': 'GBP/USD', 'type': 'forex'},
            {'symbol': 'AUDUSD', 'name': 'AUD/USD', 'type': 'forex'},
            {'symbol': 'USDJPY', 'name': 'USD/JPY', 'type': 'forex'},
            {'symbol': 'USDCAD', 'name': 'USD/CAD', 'type': 'forex'},
            {'symbol': 'BTCUSD', 'name': 'Bitcoin/USD', 'type': 'crypto'},
            {'symbol': 'ETHUSD', 'name': 'Ethereum/USD', 'type': 'crypto'}
        ]
        
        # Histórico de sinais
        self.signals_history = []
        
    def calculate_moving_averages(self, prices: List[float]) -> Dict[str, Any]:
        """
        Calcular médias móveis e seus cruzamentos
        """
        if len(prices) < 50:
            return {'signal': 'neutral', 'score': 0, 'details': {}}
        
        # Calcular diferentes médias móveis
        ma_7 = sum(prices[-7:]) / 7 if len(prices) >= 7 else prices[-1]
        ma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else prices[-1]
        ma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else prices[-1]
        ma_100 = sum(prices[-100:]) / 100 if len(prices) >= 100 else prices[-1]
        ma_200 = sum(prices[-200:]) / 200 if len(prices) >= 200 else prices[-1]
        
        current_price = prices[-1]
        
        # Análise de cruzamentos
        score = 0
        signal = 'neutral'
        
        # Golden Cross (7 > 20 > 50)
        if ma_7 > ma_20 > ma_50 > ma_100:
            score += 30
            signal = 'buy'
        
        # Death Cross (7 < 20 < 50)
        elif ma_7 < ma_20 < ma_50 < ma_100:
            score -= 30
            signal = 'sell'
        
        # Preço acima das médias
        if current_price > ma_20 and current_price > ma_50:
            score += 15
        elif current_price < ma_20 and current_price < ma_50:
            score -= 15
        
        # Convergência/Divergência
        ma_diff_20_50 = ((ma_20 - ma_50) / ma_50) * 100
        if abs(ma_diff_20_50) < 0.5:  # Médias próximas - possível reversão
            if ma_diff_20_50 > 0:
                score -= 10  # Pode estar sobrecomprado
            else:
                score += 10  # Pode estar sobrevendido
        
        return {
            'signal': signal,
            'score': score,
            'details': {
                'ma_7': round(ma_7, 5),
                'ma_20': round(ma_20, 5),
                'ma_50': round(ma_50, 5),
                'ma_100': round(ma_100, 5),
                'ma_200': round(ma_200, 5)
            }
        }
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Dict[str, Any]:
        """
        Calcular RSI (Relative Strength Index)
        """
        if len(prices) < period + 1:
            return {'signal': 'neutral', 'score': 0, 'value': 50}
        
        # Calcular ganhos e perdas
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
        
        # Média dos ganhos e perdas
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Gerar sinal baseado no RSI
        score = 0
        signal = 'neutral'
        
        if rsi < 30:
            score = 25  # Sobreventido - sinal de compra
            signal = 'buy'
        elif rsi < 40:
            score = 15  # Próximo de sobreventido
            signal = 'buy'
        elif rsi > 70:
            score = -25  # Sobrecomprado - sinal de venda
            signal = 'sell'
        elif rsi > 60:
            score = -15  # Próximo de sobrecomprado
            signal = 'sell'
        
        # Divergências
        if len(prices) > period * 2:
            if prices[-1] < prices[-period] and rsi > rsi:  # Divergência de alta
                score += 10
            elif prices[-1] > prices[-period] and rsi < rsi:  # Divergência de baixa
                score -= 10
        
        return {
            'signal': signal,
            'score': score,
            'value': round(rsi, 2),
            'details': {
                'rsi': round(rsi, 2),
                'condition': 'sobrevendido' if rsi < 30 else 'sobrecomprado' if rsi > 70 else 'neutro'
            }
        }
    
    def calculate_macd(self, prices: List[float]) -> Dict[str, Any]:
        """
        Calcular MACD (Moving Average Convergence Divergence)
        """
        if len(prices) < 26:
            return {'signal': 'neutral', 'score': 0, 'details': {}}
        
        # Calcular EMA de 12 e 26 períodos
        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        
        # MACD Line
        macd_line = ema_12[-1] - ema_26[-1]
        
        # Signal Line (EMA de 9 do MACD)
        macd_values = [ema_12[i] - ema_26[i] for i in range(len(ema_12))]
        signal_line = self.calculate_ema(macd_values, 9)[-1] if len(macd_values) >= 9 else macd_line
        
        # Histograma
        histogram = macd_line - signal_line
        
        # Gerar sinal
        score = 0
        signal = 'neutral'
        
        # Cruzamento da linha MACD com a linha de sinal
        if len(macd_values) >= 2:
            prev_macd = macd_values[-2] - (self.calculate_ema(macd_values[:-1], 9)[-1] if len(macd_values) > 9 else macd_values[-2])
            
            if histogram > 0 and prev_macd <= 0:
                score = 30  # Cruzamento de alta
                signal = 'buy'
            elif histogram < 0 and prev_macd >= 0:
                score = -30  # Cruzamento de baixa
                signal = 'sell'
            elif histogram > 0:
                score = 15  # Momentum positivo
                signal = 'buy'
            elif histogram < 0:
                score = -15  # Momentum negativo
                signal = 'sell'
        
        return {
            'signal': signal,
            'score': score,
            'details': {
                'macd': round(macd_line, 5),
                'signal': round(signal_line, 5),
                'histogram': round(histogram, 5),
                'trend': 'alta' if histogram > 0 else 'baixa'
            }
        }
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calcular EMA (Exponential Moving Average)
        """
        if len(prices) < period:
            return prices
        
        ema = []
        multiplier = 2 / (period + 1)
        
        # Primeiro EMA é a SMA
        sma = sum(prices[:period]) / period
        ema.append(sma)
        
        # Calcular EMA para os períodos restantes
        for price in prices[period:]:
            ema_value = (price - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_value)
        
        return ema
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, num_std: int = 2) -> Dict[str, Any]:
        """
        Calcular Bandas de Bollinger
        """
        if len(prices) < period:
            return {'signal': 'neutral', 'score': 0, 'details': {}}
        
        # Calcular média móvel
        ma = sum(prices[-period:]) / period
        
        # Calcular desvio padrão
        variance = sum((p - ma) ** 2 for p in prices[-period:]) / period
        std_dev = math.sqrt(variance)
        
        # Calcular bandas
        upper_band = ma + (std_dev * num_std)
        lower_band = ma - (std_dev * num_std)
        current_price = prices[-1]
        
        # Calcular largura da banda (volatilidade)
        bandwidth = ((upper_band - lower_band) / ma) * 100
        
        # Gerar sinal
        score = 0
        signal = 'neutral'
        
        # Preço tocando as bandas
        if current_price <= lower_band:
            score = 30  # Preço na banda inferior - possível compra
            signal = 'buy'
        elif current_price >= upper_band:
            score = -30  # Preço na banda superior - possível venda
            signal = 'sell'
        
        # Aperto das bandas (baixa volatilidade)
        if bandwidth < 5:
            if signal == 'buy':
                score += 10  # Confirmação de compra
            elif signal == 'sell':
                score -= 10  # Confirmação de venda
        
        return {
            'signal': signal,
            'score': score,
            'details': {
                'upper': round(upper_band, 5),
                'middle': round(ma, 5),
                'lower': round(lower_band, 5),
                'bandwidth': round(bandwidth, 2),
                'position': 'acima' if current_price > upper_band else 'abaixo' if current_price < lower_band else 'dentro'
            }
        }
    
    def calculate_stochastic(self, prices: List[float], period: int = 14) -> Dict[str, Any]:
        """
        Calcular Oscilador Estocástico
        """
        if len(prices) < period:
            return {'signal': 'neutral', 'score': 0, 'k': 50, 'd': 50}
        
        # Calcular %K
        period_high = max(prices[-period:])
        period_low = min(prices[-period:])
        current_close = prices[-1]
        
        if period_high == period_low:
            k = 50
        else:
            k = ((current_close - period_low) / (period_high - period_low)) * 100
        
        # Calcular %D (média de 3 períodos do %K)
        d_values = []
        for i in range(1, 4):
            if len(prices) >= period + i:
                high = max(prices[-(period + i):-i + 1] if i > 1 else prices[-period:])
                low = min(prices[-(period + i):-i + 1] if i > 1 else prices[-period:])
                close = prices[-i]
                if high != low:
                    d_values.append(((close - low) / (high - low)) * 100)
        
        d = sum(d_values) / len(d_values) if d_values else k
        
        # Gerar sinal
        score = 0
        signal = 'neutral'
        
        # Condições de sobrecomprado/sobrevendido
        if k < 20:
            score = 20
            signal = 'buy'
        elif k > 80:
            score = -20
            signal = 'sell'
        
        # Cruzamento %K e %D
        if k > d and k < 30:
            score += 10  # Cruzamento de alta em região de sobrevenda
        elif k < d and k > 70:
            score -= 10  # Cruzamento de baixa em região de sobrecompra
        
        return {
            'signal': signal,
            'score': score,
            'k': round(k, 2),
            'd': round(d, 2),
            'details': {
                'k': round(k, 2),
                'd': round(d, 2),
                'condition': 'sobrevendido' if k < 20 else 'sobrecomprado' if k > 80 else 'neutro'
            }
        }
    
    def calculate_volume_signal(self, prices: List[float], volumes: List[float] = None) -> Dict[str, Any]:
        """
        Calcular sinal baseado em volume (se disponível)
        """
        if not volumes or len(volumes) < 20:
            # Simular volume se não disponível
            volumes = [random.uniform(100, 1000) for _ in range(len(prices))]
        
        score = 0
        signal = 'neutral'
        
        # Comparar volume atual com média
        avg_volume = sum(volumes[-20:]) / 20
        current_volume = volumes[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume alto confirma movimento
        if volume_ratio > 1.5:
            if prices[-1] > prices[-2]:  # Preço subindo com volume alto
                score = 15
                signal = 'buy'
            elif prices[-1] < prices[-2]:  # Preço caindo com volume alto
                score = -15
                signal = 'sell'
        # Volume baixo indica fraqueza
        elif volume_ratio < 0.5:
            if prices[-1] > prices[-2]:  # Preço subindo com volume baixo
                score = -10  # Movimento fraco
            elif prices[-1] < prices[-2]:  # Preço caindo com volume baixo
                score = 10  # Possível reversão
        
        return {
            'signal': signal,
            'score': score,
            'details': {
                'volume_ratio': round(volume_ratio, 2),
                'current_volume': round(current_volume, 0),
                'avg_volume': round(avg_volume, 0)
            }
        }
    
    def calculate_trend_strength(self, prices: List[float]) -> Dict[str, Any]:
        """
        Calcular força da tendência usando regressão linear
        """
        if len(prices) < 20:
            return {'signal': 'neutral', 'score': 0, 'strength': 0}
        
        # Usar regressão linear para determinar tendência
        x = list(range(len(prices[-20:])))
        y = prices[-20:]
        
        # Calcular coeficiente angular
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        else:
            slope = 0
        
        # Calcular R² (qualidade do ajuste)
        y_mean = sum_y / n
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        ss_reg = sum(((slope * x[i] + (sum_y - slope * sum_x) / n) - y_mean) ** 2 for i in range(n))
        
        r_squared = ss_reg / ss_tot if ss_tot > 0 else 0
        
        # Gerar sinal baseado na força da tendência
        score = 0
        signal = 'neutral'
        
        if abs(slope) > 0.01 and r_squared > 0.7:
            if slope > 0:
                score = 20
                signal = 'buy'
            else:
                score = -20
                signal = 'sell'
        elif abs(slope) > 0.005 and r_squared > 0.5:
            if slope > 0:
                score = 10
                signal = 'buy'
            else:
                score = -10
                signal = 'sell'
        
        return {
            'signal': signal,
            'score': score,
            'details': {
                'slope': round(slope, 5),
                'r_squared': round(r_squared, 3),
                'strength': 'forte' if r_squared > 0.7 else 'média' if r_squared > 0.5 else 'fraca'
            }
        }
    
    def generate_signal_for_asset(self, asset: Dict, price_data: List[float], volume_data: List[float] = None) -> Dict[str, Any]:
        """
        Gerar sinal completo para um ativo específico
        """
        try:
            # Calcular todos os indicadores
            ma_result = self.calculate_moving_averages(price_data)
            rsi_result = self.calculate_rsi(price_data)
            macd_result = self.calculate_macd(price_data)
            bb_result = self.calculate_bollinger_bands(price_data)
            stoch_result = self.calculate_stochastic(price_data)
            volume_result = self.calculate_volume_signal(price_data, volume_data)
            trend_result = self.calculate_trend_strength(price_data)
            
            # Calcular pontuação total ponderada
            total_score = (
                ma_result['score'] * self.indicator_weights['moving_averages'] +
                rsi_result['score'] * self.indicator_weights['rsi'] +
                macd_result['score'] * self.indicator_weights['macd'] +
                bb_result['score'] * self.indicator_weights['bollinger'] +
                stoch_result['score'] * self.indicator_weights['stochastic'] +
                volume_result['score'] * self.indicator_weights['volume'] +
                trend_result['score'] * self.indicator_weights['trend']
            )
            
            # Normalizar pontuação para 0-100
            normalized_score = min(max(total_score + 50, 0), 100)
            
            # Determinar sinal e força
            if normalized_score >= self.signal_thresholds['strong_buy']:
                signal = 'STRONG_BUY'
                action = 'buy'
                confidence = 'ALTA'
            elif normalized_score >= self.signal_thresholds['buy']:
                signal = 'BUY'
                action = 'buy'
                confidence = 'MÉDIA'
            elif normalized_score >= self.signal_thresholds['neutral']:
                signal = 'NEUTRAL'
                action = 'neutral'
                confidence = 'BAIXA'
            elif normalized_score >= self.signal_thresholds['sell']:
                signal = 'SELL'
                action = 'sell'
                confidence = 'MÉDIA'
            else:
                signal = 'STRONG_SELL'
                action = 'sell'
                confidence = 'ALTA'
            
            # Calcular probabilidade de acerto
            probability = min(abs(normalized_score - 50) * 2 + 50, 95)
            
            # Preparar resultado
            result = {
                'asset': asset['symbol'],
                'asset_name': asset['name'],
                'asset_type': asset['type'],
                'current_price': price_data[-1] if price_data else 0,
                'signal': signal,
                'action': action,
                'score': round(normalized_score, 2),
                'probability': round(probability, 2),
                'confidence': confidence,
                'indicators': {
                    'moving_averages': {
                        'signal': ma_result['signal'],
                        'value': ma_result['details'],
                        'weight': self.indicator_weights['moving_averages']
                    },
                    'rsi': {
                        'signal': rsi_result['signal'],
      
