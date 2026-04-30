# Risk Policy

The canonical development risk policy lives in `config/risk_policy.yaml`.

Hard limits are immutable at runtime:

- Max position size per trade: 10% of equity
- Max total exposure: 100% of equity
- Max leverage: 3x
- Absolute max daily loss: 5%

Future code must treat these values as boot-time constraints, not live-editable settings.

