class TargetPrice:
    def __init__(self, id: int, price: float):
        self.id = id
        self.price = price

    def __str__(self):
        return f"TargetPrice({self.id}, {self.price})"


class TrailPrice:
    def __init__(self, id: int, price: float):
        self.id = id
        self.price = price

    def __str__(self):
        return f"TrailPrice({self.id}, {self.price})"


class StopPrice:
    def __init__(self, id: int, price: float):
        self.id = id
        self.price = price

    def __str__(self):
        return f"StopPrice({self.id}, {self.price})"

class Trade:
    def __init__(self, id: int, symbol: str, quantity: int, price: float,
                 target_price: TargetPrice, trail_price: TrailPrice, stop_price: StopPrice):
        self.id = id
        self.symbol = symbol
        self.quantity = quantity
        self.price = price
        self.target_price = target_price
        self.trail_price = trail_price
        self.stop_price = stop_price

    def __str__(self):
        return f"Trade({self.id}, {self.symbol}, {self.quantity}, {self.price},\
                  {self.target_price}, {self.trail_price}, {self.stop_price})"