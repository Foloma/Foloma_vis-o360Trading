import json
import logging
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class AffiliateSystem:
    """Sistema de afiliados para ganhar comissões"""
    
    def __init__(self):
        self.referrals = deque(maxlen=1000)  # Histórico de indicações
        self.commissions = {
            'total': 0,
            'pending': 0,
            'paid': 0,
            'history': deque(maxlen=100)
        }
        
    def generate_referral_link(self, user_id):
        """Gera link de indicação único"""
        import hashlib
        import base64
        
        # Cria código único baseado no user_id
        code = base64.b64encode(hashlib.md5(str(user_id).encode()).digest())[:8].decode()
        return f"https://foloma.com/ref/{code}"
    
    def track_referral(self, referrer_id, new_user_id):
        """Regista uma nova indicação"""
        referral = {
            'referrer_id': referrer_id,
            'new_user_id': new_user_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending',
            'commission': 0
        }
        self.referrals.append(referral)
        logger.info(f"📢 Nova indicação: {referrer_id} -> {new_user_id}")
        return referral
    
    def calculate_commission(self, trade_amount, markup_percentage):
        """Calcula comissão baseada no markup"""
        commission = trade_amount * (markup_percentage / 100)
        self.commissions['total'] += commission
        self.commissions['pending'] += commission
        return commission
    
    def get_affiliate_stats(self):
        """Retorna estatísticas do afiliado"""
        return {
            'total_referrals': len(self.referrals),
            'total_commission': round(self.commissions['total'], 2),
            'pending_commission': round(self.commissions['pending'], 2),
            'paid_commission': round(self.commissions['paid'], 2)
        }

affiliate = AffiliateSystem()
