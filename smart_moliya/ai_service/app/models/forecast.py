import torch
from torch import nn


class LinearTrendModel(nn.Module):
    """Kunlik xarajat trendini chiziqli regressiya bilan modellashtiradi (PyTorch)."""

    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)


def fit_linear_trend(daily_values: list[float], epochs: int = 500, lr: float = 0.01) -> tuple[float, float]:
    """`daily_values` bo'yicha chiziqli trend (slope, intercept) ni qaytaradi."""
    if len(daily_values) < 2:
        avg = daily_values[0] if daily_values else 0.0
        return 0.0, avg

    days = torch.arange(len(daily_values), dtype=torch.float32).unsqueeze(1)
    values = torch.tensor(daily_values, dtype=torch.float32).unsqueeze(1)

    # Adam qadam kattaligi parametr masshtabidan qariyb mustaqil bo'lgani uchun
    # (10000 so'mlik summalarda yaqinlashish million qadam talab qilardi),
    # ham kunlarni, ham summalarni normallashtirib o'qitamiz, so'ng asl masshtabga qaytaramiz.
    day_mean = float(days.mean().item())
    day_std = float(days.std().item()) + 1e-6
    value_mean = float(values.mean().item())
    value_std = float(values.std().item()) + 1e-6

    days_norm = (days - day_mean) / day_std
    values_norm = (values - value_mean) / value_std

    model = LinearTrendModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        prediction = model(days_norm)
        loss = loss_fn(prediction, values_norm)
        loss.backward()
        optimizer.step()

    model.eval()
    weight = model.linear.weight.item()
    bias = model.linear.bias.item()

    # y_norm = weight * x_norm + bias, x_norm=(x-day_mean)/day_std, y_norm=(y-value_mean)/value_std
    # => y = value_std*weight/day_std * x + (value_std*(bias - weight*day_mean/day_std) + value_mean)
    slope = value_std * weight / day_std
    intercept = value_std * (bias - weight * day_mean / day_std) + value_mean
    return slope, intercept
