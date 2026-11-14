"""Forecast each Polymarket event market for four hours using recent volatility, zero drift, and clipped mutual-exclusivity normalization."""

import json
import math
import os


QUANTILE_Z = (-1.644854, -0.539592, 0.0, 0.539592, 1.644854)


def market_sigma(prices, x):
    """Compute the clamped volatility scale from at most the latest 61 prices."""
    if len(prices) < 2:
        mean_abs = 0.0
    else:
        recent = prices[-61:]
        mean_abs = sum(
            abs(recent[i + 1] - recent[i]) for i in range(len(recent) - 1)
        ) / (len(recent) - 1)
    sigma = mean_abs + 0.003 * math.sqrt(x * (1.0 - x))
    return min(0.005, max(0.0002, sigma))


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    for filename in sorted(name for name in os.listdir(input_dir) if name.endswith(".in")):
        with open(os.path.join(input_dir, filename), "r", encoding="utf-8") as source:
            case = json.load(source)

        markets = case["markets"]
        last_prices = [market["prices"][-1] for market in markets]
        price_sum = sum(last_prices)
        if price_sum == 0:
            scale = 1.0
        else:
            scale = 1.0 / price_sum
        scale = min(1.08, max(0.92, scale))

        forecasts = []
        for market, x in zip(markets, last_prices):
            sigma = market_sigma(market["prices"], x)

            rows = []
            for h in range(1, case["horizon_minutes"] + 1):
                spread = sigma * math.sqrt(h)
                row = []
                for z in QUANTILE_Z:
                    value = min(1.0, max(0.0, (x + z * spread) * scale))
                    rounded = round(value, 6)
                    row.append(0.0 if rounded == 0 else rounded)
                rows.append(row)
            forecasts.append({"id": market["id"], "q": rows})

        output = {"forecasts": forecasts}
        output_name = f"{case['case']}.out"
        with open(os.path.join(output_dir, output_name), "w", encoding="utf-8", newline="\n") as target:
            json.dump(output, target, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


if __name__ == "__main__":
    main()
