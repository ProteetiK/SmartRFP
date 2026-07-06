"""
backend/tools/calculator_tool.py — PricingCalculator.

Pure cost math over ResourceRate rows (backend/models.py). This file did not
exist even though backend/services/estimation_service.py has always imported
it (`from backend.tools.calculator_tool import PricingCalculator`), which
meant importing backend.services — and therefore backend.main — crashed with
`ModuleNotFoundError: No module named 'backend.tools'`.

No LLM, no I/O: given resource rates + effort-by-role, compute a costed
line-item breakdown. Used by EstimationService alongside PricingService
(DB rates) and TavilyTool (live market insight).
"""
from typing import Dict, Iterable, List


class PricingCalculator:
    """Stateless calculator: given resource rates and effort, compute cost."""

    @staticmethod
    def line_item(role: str, hours: float, hourly_rate: float, currency: str = "INR") -> Dict:
        total = round(float(hours) * float(hourly_rate), 2)
        return {
            "role": role,
            "hours": hours,
            "hourly_rate": float(hourly_rate),
            "total": total,
            "currency": currency,
        }

    def estimate(self, effort_by_role: Dict[str, float], rates: Iterable) -> List[Dict]:
        """
        effort_by_role: {"Developer": 480, "QA": 120, ...}
        rates: iterable of ResourceRate rows (must have .role / .hourly_rate /
               .currency attributes — e.g. from PricingService.get_all_rates()).

        Roles with no matching rate are silently skipped (no fabricated
        pricing) rather than raising, so a partially-populated rate card
        still produces a usable partial estimate.
        """
        rate_by_role = {r.role: r for r in rates}
        lines = []
        for role, hours in effort_by_role.items():
            rate = rate_by_role.get(role)
            if not rate:
                continue
            lines.append(self.line_item(role, hours, float(rate.hourly_rate), rate.currency or "INR"))
        return lines

    @staticmethod
    def total(lines: Iterable[Dict]) -> float:
        return round(sum(l["total"] for l in lines), 2)