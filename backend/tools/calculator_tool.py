from typing import Dict, Iterable, List


class PricingCalculator:

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