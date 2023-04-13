from Game import RiskGame
from pygame import Surface

GAME = RiskGame(Surface((500, 500)))
color = "Green"

test_cards_1 = [("Nigeria", "Cavalry"), ("Nigeria", "Cavalry"), ("Siam", "Cavalry")]
test_cards_2 = [("Nigeria", "Cavalry"), ("Siam", "Artillery"), ("Siam", "Infantry")]
test_cards_3 = [("Nigeria", "Cavalry"), ("Siam", "Infantry"), ("Nigeria", "Wild")]
test_cards_4 = [("Nigeria", "Cavalry"), ("Siam", "Cavalry"), ("Wild", "Wild")]

test_cards_5 = [("Siam", "Cavalry"), ("Nigeria", "Infantry"), ("Wild", "Wild"), ("Siam", "Cavalry")]

GAME.TERRITORIES_OWNED[color] = ["China", "Siam"]
GAME.CARDS_OWNED[color] = test_cards_5

print(GAME._get_card_trade_bonus(color))