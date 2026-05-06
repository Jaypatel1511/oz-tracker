"""
OZ Investment Portfolio Tracker.
Track QOF investments, holding periods, and aggregate tax benefits.
"""
from typing import Optional
import pandas as pd

from oztracker.data.schema import OZInvestment, FUND_TYPES, OZ_VERSIONS
from oztracker.benefits.qof import calculate_benefits


class OZPortfolio:
    """
    Track a portfolio of Qualified Opportunity Fund investments.

    Usage:
        p = OZPortfolio(name="Family OZ Portfolio")
        p.add(investment1)
        p.add(investment2)
        p.summary()
    """

    def __init__(self, name: str):
        self.name = name
        self._investments: list[OZInvestment] = []

    def add(self, investment: OZInvestment) -> None:
        if not isinstance(investment, OZInvestment):
            raise TypeError("Only OZInvestment objects can be added.")
        if any(i.id == investment.id for i in self._investments):
            raise ValueError(f"Investment '{investment.id}' already exists.")
        self._investments.append(investment)

    def remove(self, investment_id: str) -> None:
        self._investments = [
            i for i in self._investments if i.id != investment_id
        ]

    def count(self) -> int:
        return len(self._investments)

    def get(self, investment_id: str) -> Optional[OZInvestment]:
        for inv in self._investments:
            if inv.id == investment_id:
                return inv
        return None

    def filter_oz_version(self, version: str) -> list:
        return [i for i in self._investments if i.oz_version == version]

    def filter_rural(self) -> list:
        return [i for i in self._investments if i.is_rural]

    def filter_fund_type(self, fund_type: str) -> list:
        return [i for i in self._investments if i.fund_type == fund_type]

    @property
    def total_invested(self) -> float:
        return sum(i.capital_gain_invested for i in self._investments)

    @property
    def oz1_invested(self) -> float:
        return sum(i.capital_gain_invested for i in self._investments
                   if i.oz_version == "oz1")

    @property
    def oz2_invested(self) -> float:
        return sum(i.capital_gain_invested for i in self._investments
                   if i.oz_version == "oz2")

    @property
    def rural_invested(self) -> float:
        return sum(i.capital_gain_invested for i in self._investments
                   if i.is_rural)

    def total_tax_benefits(self, tax_rate: float = 0.238) -> float:
        total = 0.0
        for inv in self._investments:
            benefits = calculate_benefits(inv, tax_rate=tax_rate)
            total += benefits.total_tax_benefit
        return total

    def summary(self, tax_rate: float = 0.238) -> None:
        print(f"\nOZ Investment Portfolio — {self.name}")
        print("=" * 55)
        print(f"\nPORTFOLIO OVERVIEW")
        print(f"  Total Investments:     {self.count()}")
        print(f"  Total Capital Gains:   ${self.total_invested/1e6:.2f}MM")
        print(f"  OZ 1.0 Investments:    ${self.oz1_invested/1e6:.2f}MM")
        print(f"  OZ 2.0 Investments:    ${self.oz2_invested/1e6:.2f}MM")
        print(f"  Rural QORF:            ${self.rural_invested/1e6:.2f}MM")

        total_benefit = self.total_tax_benefits(tax_rate)
        print(f"\nTAX BENEFITS (est. @ {tax_rate*100:.1f}% cap gains rate)")
        print(f"  Total Tax Benefit:     ${total_benefit/1e6:.2f}MM")
        if self.total_invested > 0:
            print(f"  Benefit as % of Gain:  "
                  f"{total_benefit/self.total_invested*100:.1f}%")

        states = set(i.state for i in self._investments if i.state)
        if states:
            print(f"\nGEOGRAPHY")
            print(f"  States:               {', '.join(sorted(states))}")
        print()

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for i in self._investments:
            rows.append({
                "id": i.id,
                "investor": i.investor_name,
                "fund": i.fund_name,
                "fund_type": i.fund_type,
                "oz_version": i.oz_version,
                "tract_id": i.tract_id,
                "investment_type": i.investment_type,
                "capital_gain": i.capital_gain_invested,
                "investment_date": i.investment_date,
                "state": i.state,
                "is_rural": i.is_rural,
            })
        return pd.DataFrame(rows)
