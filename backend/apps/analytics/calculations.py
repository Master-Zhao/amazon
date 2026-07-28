from decimal import Decimal


def calculate_metrics(*, impressions, clicks, spend, orders, sales):
    impressions = int(impressions)
    clicks = int(clicks)
    spend = Decimal(str(spend))
    orders = int(orders)
    sales = Decimal(str(sales))
    reasons = {}

    def ratio(numerator, denominator, key, reason):
        if denominator <= 0:
            reasons[key] = reason
            return None
        return Decimal(numerator) / Decimal(denominator)

    return {
        "ctr": ratio(clicks, impressions, "ctr", "NO_IMPRESSIONS"),
        "cpc": ratio(spend, clicks, "cpc", "NO_CLICKS"),
        "cvr": ratio(orders, clicks, "cvr", "NO_CLICKS"),
        "acos": ratio(spend, sales, "acos", "NO_SALES"),
        "roas": ratio(sales, spend, "roas", "NO_SPEND"),
        "invalid_reasons": reasons,
    }

