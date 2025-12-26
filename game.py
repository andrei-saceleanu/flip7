import random
import string
from enum import Enum

WIN_SCORE = 200
BONUS_FLIP7 = 15


def generate_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


class CardType(Enum):
    NUMBER = "number"
    SECOND_CHANCE = "second_chance"
    FREEZE = "freeze"
    FLIP_7 = "flip_7"


class Card:
    def __init__(self, type, value=None, target=None):
        self.type = type
        self.value = value
        self.target = target

    def to_dict(self):
        return {"type": self.type.value, "value": self.value}


class Deck:
    def __init__(self):
        self.cards = self._init_deck()

    def _init_deck(self):
        cards = []

        for n in range(1,13):
            for _ in range(n):
                cards.append(Card(CardType.NUMBER, n))
        cards.append(Card(CardType.NUMBER, 0))
        cards += [Card(CardType.SECOND_CHANCE) for _ in range(3)]
        cards += [Card(CardType.FREEZE) for _ in range(3)]

        for _ in range(10):
            random.shuffle(cards)

        return cards

    def draw(self):
        res = self.cards.pop()
        if len(self.cards) == 0:
            self.cards = self._init_deck()
        return res


class Player:
    def __init__(self, name, sid):
        self.name = name
        self.sid = sid
        self.total_score = 0
        self.reset_round()

    def reset_round(self):
        self.numbers = set()
        self.cards = []
        self.second_chance = 0
        self.busted = False
        self.finished = False
        self.flip7 = False

    def round_score(self):
        if self.busted:
            return 0
        res = sum(self.numbers)
        if self.flip7:
            res += BONUS_FLIP7
        return res

    def to_dict(self):
        return {
            "sid": self.sid,
            "name": self.name,
            "round_score": self.round_score(),
            "total_score": self.total_score,
            "numbers": sorted(self.numbers),
            "cards": [c.to_dict() for c in self.cards],
            "second_chance": self.second_chance,
            "busted": self.busted,
            "finished": self.finished,
            "flip7": self.flip7
        }


class Game:
    def __init__(self, owner_sid):
        self.code = generate_code()
        self.owner_sid = owner_sid
        self.players = []
        self.started = False
        self.round = 1
        self.turn = 0
        self.deck = Deck()
        self.match_winner = None

        self.pending_freeze = None

    def add_player(self, name, sid):
        if self.started:
            return False
        self.players.append(Player(name, sid))
        return True

    def start(self, sid):
        if sid != self.owner_sid:
            return False
        self.started = True
        return True

    def current_player(self):
        return self.players[self.turn]
    
    def get_player_by_sid(self, sid):
        return next(p for p in self.players if p.sid == sid)

    def next_turn(self):
        for _ in range(len(self.players)):
            self.turn = (self.turn + 1) % len(self.players)
            if not self.players[self.turn].finished:
                return

    def hit(self, sid):
        if not self.started or self.match_winner or self.pending_freeze:
            return

        p = self.current_player()
        if p.sid != sid or p.finished:
            return

        card = self.deck.draw()
        p.cards.append(card)

        if card.type == CardType.NUMBER:
            if card.value in p.numbers:
                if p.second_chance > 0:
                    p.second_chance -= 1
                else:
                    p.busted = True
                    p.finished = True
            else:
                p.numbers.add(card.value)
                if len(p.numbers) == 7:
                    p.finished = True
                    p.flip7 = True

        elif card.type == CardType.SECOND_CHANCE:
            p.second_chance += 1

        elif card.type == CardType.FREEZE:
            self.pending_freeze = p.sid  # must choose target
            return
        
        self.next_turn()

        self.check_round_end()

    def stay(self, sid):
        if not self.started or self.match_winner or self.pending_freeze:
            return

        p = self.current_player()
        if p.sid != sid:
            return

        p.finished = True
        self.next_turn()
        self.check_round_end()

    def apply_freeze(self, sid, target_sid):
        if self.pending_freeze != sid:
            return

        target = self.get_player_by_sid(target_sid)
        if target.finished:
            return

        target.finished = True

        # annotate last freeze card
        freezer = self.get_player_by_sid(sid)
        freezer.cards[-1].target = target.name

        self.pending_freeze = None

        self.next_turn()
        self.check_round_end()

    def check_round_end(self):
        if not all(p.finished for p in self.players):
            return

        for p in self.players:
            p.total_score += p.round_score()

        max_score = -1
        is_winner = False
        for p in self.players:
            if p.total_score >= WIN_SCORE:
                if p.total_score > max_score:
                    self.match_winner = p
                    max_score = p.total_score
                is_winner = True
        if is_winner:
            return

        self.start_new_round()

    def start_new_round(self):
        self.round += 1
        self.turn = (self.turn + 1) % len(self.players)
        self.pending_freeze = None
        for p in self.players:
            p.reset_round()

    def to_dict(self):
        return {
            "code": self.code,
            "started": self.started,
            "round": self.round,
            "turn": self.turn,
            "pending_freeze": self.pending_freeze,
            "match_winner": self.match_winner.name if self.match_winner else None,
            "players": [p.to_dict() for p in self.players]
        }
