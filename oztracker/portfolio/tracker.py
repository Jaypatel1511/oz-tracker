"""
OZ Investment Portfolio Tracker.
Track QOF investments, holding periods, and aggregate tax benefits.
"""
from typing import Optional
import pandas as pd

from oztracker.data.schema import OZInvestment, FUND_TYPES, OZ_VERSIONS
from oztracker.benefits.qof import calculate_benefits
from oztracker.exceptions import OZCalculationError


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

    def _partition_benefits(self, tax_rate: float = 0.238) -> tuple:
        """Split members into (computed, undeterminable).

        ``computed`` is [(investment, QOFBenefits)], ``undeterminable`` is
        [(investment, reason)]. The rule for what is determinable lives in one
        place — the raise site in ``calculate_benefits`` — and this partitions
        by catching it, rather than duplicating the date logic here where the
        two could drift apart.
        """
        computed, undeterminable = [], []
        for inv in self._investments:
            try:
                computed.append((inv, calculate_benefits(inv, tax_rate=tax_rate)))
            except OZCalculationError as e:
                undeterminable.append((inv, str(e)))
        return computed, undeterminable

    def undeterminable_benefits(self, tax_rate: float = 0.238) -> list:
        """Return [(investment, reason)] for members whose benefit cannot be
        computed — e.g. a future-dated investment with no exit_date.

        Lets a caller check coverage without catching exceptions, and is what
        ``summary()`` uses to report exclusions by name instead of dropping
        them.
        """
        return self._partition_benefits(tax_rate)[1]

    def total_tax_benefits(self, tax_rate: float = 0.238) -> float:
        """Total tax benefit across the portfolio.

        Raises OZCalculationError if ANY member's benefit is not determinable.

        This refuses rather than returning a subtotal because the return type
        is a bare ``float``: it has nowhere to carry "this covers 2 of your 3
        investments", so a caller doing ``p.total_tax_benefits()`` would get a
        number that looks complete and is not. Silently skipping the
        undeterminable members would understate the total with no signal —
        the aggregate equivalent of the fabricated negative this release
        removes.

        For a portfolio that legitimately contains not-yet-made investments,
        either supply exit dates, or use ``summary()`` (which reports the
        determinable subtotal explicitly scoped), or partition it yourself via
        ``undeterminable_benefits()``.

        An EMPTY portfolio returns 0.0 and does not raise. Nothing is
        undeterminable, because there is nothing to determine; the sum of no
        benefits is zero. That is a different statement from "there are
        investments here whose benefit has no answer", which is what the
        refusal above means. ``summary()`` agrees, printing the ordinary
        ``Total Tax Benefit: $0.00MM``.
        """
        computed, undeterminable = self._partition_benefits(tax_rate)
        if undeterminable:
            ids = ", ".join(repr(inv.id) for inv, _ in undeterminable)
            raise OZCalculationError(
                f"Cannot total tax benefits for portfolio {self.name!r}: "
                f"{len(undeterminable)} of {len(self._investments)} "
                f"investment(s) have no determinable holding period ({ids}). "
                f"Refusing to return a subtotal that would read as a complete "
                f"total. First reason: {undeterminable[0][1]}"
            )
        # float() so the empty case returns 0.0 and not sum()'s int 0 — the
        # annotation says float, and bd47b1f's accumulator started at 0.0.
        return float(sum(b.total_tax_benefit for _, b in computed))

    def summary(self, tax_rate: float = 0.238) -> None:
        print(f"\nOZ Investment Portfolio — {self.name}")
        print("=" * 55)
        print(f"\nPORTFOLIO OVERVIEW")
        print(f"  Total Investments:     {self.count()}")
        print(f"  Total Capital Gains:   ${self.total_invested/1e6:.2f}MM")
        print(f"  OZ 1.0 Investments:    ${self.oz1_invested/1e6:.2f}MM")
        print(f"  OZ 2.0 Investments:    ${self.oz2_invested/1e6:.2f}MM")
        print(f"  Rural QORF:            ${self.rural_invested/1e6:.2f}MM")

        # Unlike total_tax_benefits(), a printed report CAN carry the caveat —
        # so summary() states coverage rather than refusing. What it must never
        # do is print a bare "Total Tax Benefit" that quietly omits members.
        computed, undeterminable = self._partition_benefits(tax_rate)
        covered_gain = sum(i.capital_gain_invested for i, _ in computed)
        total_benefit = sum(b.total_tax_benefit for _, b in computed)

        print(f"\nTAX BENEFITS (est. @ {tax_rate*100:.1f}% cap gains rate)")
        if undeterminable:
            print(f"  ⚠ PARTIAL — covers {len(computed)} of "
                  f"{len(self._investments)} investments "
                  f"(${covered_gain/1e6:.2f}MM of "
                  f"${self.total_invested/1e6:.2f}MM in capital gains).")
            print(f"    This is NOT a portfolio total. See NOT DETERMINABLE below.")
        # Branch on what is EXCLUDED, not on what was computed. An empty
        # portfolio computes nothing, but nothing is excluded either: its
        # benefit is a genuine 0.0 — the sum of no benefits — and not a
        # question without an answer. Branching on `if computed:` conflated the
        # two and made summary() refuse where total_tax_benefits() returns 0.0,
        # so the package's two public entry points disagreed on the same
        # portfolio.
        #
        # The literals below are spelled out per branch rather than assembled
        # from a shared label, because the exact spacing of the complete path
        # is a compatibility surface: it is what bd47b1f printed and what the
        # README quotes. Building it from a padded label silently drifted by
        # one space on the percentage line.
        if not undeterminable:
            print(f"  Total Tax Benefit:     ${total_benefit/1e6:.2f}MM")
            if covered_gain > 0:
                print(f"  Benefit as % of Gain:  "
                      f"{total_benefit/covered_gain*100:.1f}%")
        elif computed:
            print(f"  Benefit (covered subset): ${total_benefit/1e6:.2f}MM")
            if covered_gain > 0:
                # Denominator is covered_gain, NOT self.total_invested: this
                # figure is scoped to the members that were actually computed,
                # and the line above says so. Dividing the covered benefit by
                # the full portfolio's gain would print a percentage whose
                # label contradicts its value.
                print(f"  % of covered gain:     "
                      f"{total_benefit/covered_gain*100:.1f}%")
        else:
            print(f"  No benefit figure can be computed for any investment "
                  f"in this portfolio.")

        if undeterminable:
            print(f"\nNOT DETERMINABLE ({len(undeterminable)} of "
                  f"{len(self._investments)})")
            print(f"  These investments are EXCLUDED from the figure above and "
                  f"are not zero —")
            print(f"  their benefit has no answer from the inputs given:")
            for inv, reason in undeterminable:
                print(f"    • {inv.id} ({inv.fund_name}): "
                      f"${inv.capital_gain_invested/1e6:.2f}MM")
                print(f"      {reason}")

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
