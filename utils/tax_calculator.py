class TaxCalculator:
    """
    Calculates charges for NSE/BSE Equity Intraday trades.
    Standard Zerodha/Dhan based charges (approximate).
    """
    def __init__(self, brokerage_rate=0.0003, max_brokerage=20):
        self.brokerage_rate = brokerage_rate
        self.max_brokerage = max_brokerage
        self.stt_rate = 0.00025 # On sell side for intraday
        self.txn_charge_rate = 0.0000325 # NSE
        self.gst_rate = 0.18 # 18% on (brokerage + txn charges)
        self.sebi_rate = 0.0000001 # ₹10 / crore
        self.stamp_duty_rate = 0.00003 # ₹300 / crore on buy side

    def calculate_costs(self, buy_price: float, sell_price: float, quantity: int) -> dict:
        turnover = (buy_price + sell_price) * quantity
        
        # 1. Brokerage
        buy_brokerage = min(self.max_brokerage, buy_price * quantity * self.brokerage_rate)
        sell_brokerage = min(self.max_brokerage, sell_price * quantity * self.brokerage_rate)
        total_brokerage = buy_brokerage + sell_brokerage
        
        # 2. STT (Only on Sell side for Intraday)
        stt = round(sell_price * quantity * self.stt_rate)
        
        # 3. Transaction Charges
        txn_charges = turnover * self.txn_charge_rate
        
        # 4. GST
        gst = (total_brokerage + txn_charges) * self.gst_rate
        
        # 5. SEBI Charges
        sebi_charges = turnover * self.sebi_rate
        
        # 6. Stamp Duty (Only on Buy side for Intraday)
        stamp_duty = buy_price * quantity * self.stamp_duty_rate
        
        total_tax = stt + txn_charges + gst + sebi_charges + stamp_duty
        total_charges = total_brokerage + total_tax
        
        net_pnl = (sell_price - buy_price) * quantity - total_charges
        breakeven = total_charges / quantity if quantity > 0 else 0
        
        return {
            "total_brokerage": total_brokerage,
            "total_tax": total_tax,
            "total_charges": total_charges,
            "net_pnl": net_pnl,
            "points_to_breakeven": breakeven
        }

if __name__ == "__main__":
    calc = TaxCalculator()
    costs = calc.calculate_costs(25000, 25050, 100)
    print(f"Costs: {costs}")
