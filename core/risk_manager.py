from dataclasses import dataclass
from typing import List

@dataclass
class Trade:
    pnl_pct: float
    is_win: bool

class RiskManager:
    def __init__(self, max_drawdown: float = 1.5, max_trades: int = 3, max_losses: int = 2):
        self.max_drawdown = max_drawdown
        self.max_trades = max_trades
        self.max_losses = max_losses
        
        self.reset_session()

    def reset_session(self):
        self.session_trades: List[Trade] = []
        self.current_drawdown = 0.0
        self.consecutive_losses = 0
        self.daily_pnl = 0.0 # Tracking absolute PnL in percentage or currency
        self.is_kill_switch_active = False

    def check_constraints(self) -> bool:
        """Returns True if trading is allowed, False otherwise."""
        if self.is_kill_switch_active:
            return False
            
        if len(self.session_trades) >= self.max_trades:
            return False
            
        if self.current_drawdown >= self.max_drawdown:
            return False
            
        if self.consecutive_losses >= self.max_losses:
            return False
            
        return True

    def record_trade(self, pnl_pct: float):
        trade = Trade(pnl_pct=pnl_pct, is_win=pnl_pct > 0)
        self.session_trades.append(trade)
        
        # Simple drawdown tracking (relative to start of session)
        session_pnl = sum(t.pnl_pct for t in self.session_trades)
        self.daily_pnl = session_pnl # Update daily PnL
        if session_pnl < 0:
            self.current_drawdown = abs(session_pnl)
        
        if not trade.is_win:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        if not self.check_constraints():
            self.is_kill_switch_active = True

    def activate_kill_switch(self):
        self.is_kill_switch_active = True
