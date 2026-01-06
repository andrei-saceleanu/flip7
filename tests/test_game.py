import pytest
from game import Game, Deck, Player, Card, CardType

def test_deck_initialization():
    deck = Deck()
    # The deck from _init_deck() contains 100 cards by default
    assert len(deck.cards) == 100
    assert isinstance(deck.cards[0], deck.cards[0].__class__)
    # Check card values and types
    card_types = [c.type for c in deck.cards]
    assert card_types.count(CardType.NUMBER) == 79  
    assert card_types.count(CardType.DISCARD) == 5

def test_deck_draw_reduces_length():
    deck = Deck()
    initial_len = len(deck.cards)
    drawn = deck.draw()
    assert len(deck.cards) == initial_len - 1
    assert drawn.__class__.__name__ == "Card"

def test_deck_reset_after_empty():
    deck = Deck()
    num_cards = len(deck.cards)
    cards_drawn = []
    for _ in range(num_cards):
        cards_drawn.append(deck.draw())
    # After num_cards draws, the reset happens immediately, so the deck should be back to full
    assert len(deck.cards) == num_cards
    new_card = deck.draw()
    # After another draw, should be back to n-1 cards
    assert len(deck.cards) == num_cards - 1
    assert new_card.__class__.__name__ == "Card"

def test_deck_draw_all_and_cycle_same():
    deck = Deck()
    num_cards = len(deck.cards)
    
    draws = [deck.draw() for _ in range(num_cards)]
    stats = extract_stats(draws)
    
    second_draws = [deck.draw() for _ in range(num_cards)]
    second_stats = extract_stats(second_draws)

    assert stats == second_stats


def test_player_init_and_reset_round():
    p = Player(name="Alice", sid="s1")
    assert p.name == "Alice"
    assert p.sid == "s1"
    assert isinstance(p.player_id, str)
    assert p.total_score == 0
    # After init or reset, round state is clear
    assert p.numbers == set()
    assert p.cards == []
    assert p.second_chance == 0
    assert not p.busted
    assert not p.finished
    assert not p.flip7

    # After reset_round, things clear
    p.numbers = {2, 4}
    p.cards.append(Card(CardType.NUMBER, 2))
    p.cards.append(Card(CardType.NUMBER, 4))
    p.cards.append(Card(CardType.NUMBER, 2))
    p.busted = True
    p.reset_round()
    assert p.numbers == set()
    assert p.cards == []
    assert p.second_chance == 0
    assert not p.busted
    assert not p.finished
    assert not p.flip7

def test_player_round_score_busted():
    p = Player(name="Bob", sid="s2")
    p.numbers = {1, 2, 3}
    p.busted = True
    assert p.round_score() == 0

def test_player_round_score_basic():
    p = Player(name="Eve", sid="s3")
    p.numbers = {1, 2, 3}
    assert p.round_score() == 6

def test_player_round_score_with_bonus_cards():
    p = Player(name="Dan", sid="s4")
    p.numbers = {2, 4}
    # +3 and x2 bonus cards
    p.cards.append(Card(CardType.BONUS, "+3"))
    p.cards.append(Card(CardType.BONUS, "x2"))
    assert p.round_score() == (2+4+3)*2 == 18

def test_player_round_score_with_multiple_multipliers():
    p = Player(name="Ginny", sid="s5")
    p.numbers = {5}
    # x2 and x3 multiplier bonus cards (+0 to keep it simple)
    p.cards.append(Card(CardType.BONUS, "x2"))
    p.cards.append(Card(CardType.BONUS, "x3"))
    assert p.round_score() == 5*2*3

def test_player_round_score_with_flip7_bonus():
    p = Player(name="Wes", sid="s6")
    p.numbers = set(range(1,8))  # 1-7
    p.flip7 = True
    score = p.round_score()
    assert score == sum(range(1,8)) + 15  # (+15 for BONUS_FLIP7)

def test_player_to_dict_format():
    p = Player(name="Sue", sid="s7", player_id="pid0")
    p.numbers = {6, 2}
    p.cards = [Card(CardType.BONUS, "+4"), Card(CardType.NUMBER, 2)]
    p.second_chance = 1
    p.busted = False
    p.finished = True
    d = p.to_dict()
    assert d["player_id"] == "pid0"
    assert d["sid"] == "s7"
    assert d["name"] == "Sue"
    assert d["numbers"] == [2, 6]
    assert d["second_chance"] == 1
    assert d["finished"] is True
    assert isinstance(d["cards"], list)
    assert {"type": "bonus", "value": "+4"} in d["cards"]
    assert {"type": "number", "value": 2} in d["cards"]

def make_card(card_type, value=None):  # helper for clarity

    return Card(card_type, value)

def make_deck(card_specs):
    # card_specs is list of (CardType, value)
    return [Card(*spec) for spec in card_specs]

def basic_two_players():
    g = Game(owner_sid='sidA', cards=make_deck([
        (CardType.NUMBER, 2), (CardType.NUMBER, 3)
    ]*10))  # Plenty of cards
    g.add_player("A", "sidA")
    g.add_player("B", "sidB")
    g.start('sidA')
    return g

def test_game_add_and_start():
    g = Game(owner_sid='owner', cards=make_deck([(CardType.NUMBER, 7)]*10))
    p1 = g.add_player("P1", "s1")
    assert p1.name == "P1"
    assert not g.started
    assert g.start('owner')
    assert g.started
    # Cannot add after start
    p2 = g.add_player("P2", "s2")
    assert p2 is None

def test_game_basic_hit_and_stay():
    g = basic_two_players()
    g.hit("sidA")

    assert len(g.players[0].cards) == 1
    assert g.turn == 1

    g.stay("sidB")
    assert g.players[1].finished
    assert g.turn == 0
    g.stay("sidA")

    # Both finished: a new round should start immediately 
    assert g.round == 2
    assert len(g.players[0].cards) == 0
    assert len(g.players[1].cards) == 0
    
 
def test_game_bust_by_duplicate_number():
    # Deck: [2, 2]
    g = Game(owner_sid='host', cards=make_deck([(CardType.NUMBER,2),(CardType.NUMBER,2)]))
    g.add_player("P", "host")
    g.start('host')
    g.hit("host")
    assert not g.players[0].busted
    g.hit("host")   
    # After bust, total score should be 0 (round has auto-increased)
    assert g.players[0].total_score == 0




def extract_stats(draws):
    card_types = [c.type for c in draws]
    
    x = [(t.value, card_types.count(t)) for t in set(card_types)]
    x.sort(key=lambda x: (x[1], x[0]))
    return x
