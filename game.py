import random
import string
import uuid
from enum import Enum

WIN_SCORE = 200
BONUS_FLIP7 = 15


def generate_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


class CardType(Enum):
    NUMBER = "number"
    SECOND_CHANCE = "second_chance"
    FREEZE = "freeze"
    FLIP_3 = "flip_three"
    BONUS = "bonus"
    DISCARD = "discard"


class Card:
    def __init__(self, type, value=None, target=None):
        self.type = type
        self.value = value
        self.target = target

    def to_dict(self):
        return {"type": self.type.value, "value": self.value}

class Deck:
    def __init__(self, cards=None):
        if cards is None:
            self.cards = self._init_deck()
            self.deterministic = False
        else:
            self.cards = cards
            self.backup = [elem for elem in cards]
            self.deterministic = True

    def _init_deck(self):
        
        cards = []

        for n in range(1,13):
            for _ in range(n):
                cards.append(Card(CardType.NUMBER, n))
        cards.append(Card(CardType.NUMBER, 0))
        cards += [Card(CardType.SECOND_CHANCE) for _ in range(3)]
        cards += [Card(CardType.FREEZE) for _ in range(3)]
        cards += [Card(CardType.FLIP_3) for _ in range(3)]
        cards += [Card(CardType.DISCARD) for _ in range(5)]
        cards += [
            Card(CardType.BONUS, "+2"),
            Card(CardType.BONUS, "+4"),
            Card(CardType.BONUS, "+6"),
            Card(CardType.BONUS, "+8"),
            Card(CardType.BONUS, "+10"),
            Card(CardType.BONUS, "x2"),
            Card(CardType.BONUS, "x2"),
        ]

        for _ in range(10):
            random.shuffle(cards)

        return cards

    def draw(self):
        res = self.cards.pop()
        if len(self.cards) == 0:
            if not self.deterministic:
                self.cards = self._init_deck() 
            else:
                self.cards = [elem for elem in self.backup]
        return res


class Player:
    def __init__(self, name, sid, player_id=None):
        self.player_id = player_id or str(uuid.uuid4())
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
        
        add_bonuses = 0
        multiplier = 1
        for elem in self.cards:     
            if elem.type == CardType.BONUS:
                if elem.value[0] == "+":
                    add_bonuses += int(elem.value[1:])
                elif elem.value[0] == "x":
                    multiplier *= int(elem.value[1:])
        
        res = (sum(self.numbers) + add_bonuses) * multiplier

        if self.flip7:
            res += BONUS_FLIP7
        return res

    def to_dict(self):
        return {
            "player_id": self.player_id,
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
    def __init__(self, owner_sid, cards=None):
        self.code = generate_code()
        self.owner_sid = owner_sid
        self.players = []
        self.started = False
        self.round = 1
        self.turn = 0
        self.deck = Deck(cards=cards)
        self.match_winner = None

        self.pending_actions = []
        self.pending_round_reset = False

    def add_player(self, name, sid, player_id=None):
        existing = self.get_player_by_player_id(player_id) if player_id else None

        if existing:
            existing.sid = sid
            existing.name = name
            return existing

        if self.started:
            return None

        p = Player(name, sid, player_id)
        self.players.append(p)
        return p

    def start(self, sid):
        if sid != self.owner_sid:
            return False
        self.started = True
        return True

    def current_player(self):
        return self.players[self.turn]
    
    def get_player_by_player_id(self, player_id):
        for p in self.players:
            if p.player_id == player_id:
                return p
        return None

    
    def get_player_by_sid(self, sid):
        return next(p for p in self.players if p.sid == sid)

    def next_turn(self):
        for _ in range(len(self.players)):
            self.turn = (self.turn + 1) % len(self.players)
            if not self.players[self.turn].finished:
                return

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

        self.pending_round_reset = True
        # self.start_new_round()

    def start_new_round(self):
        self.round += 1
        self.turn = (self.turn + 1) % len(self.players)
        self.pending_actions = []
        for p in self.players:
            p.reset_round()

    def stay(self, sid):
        if not self.started or self.match_winner or self.pending_actions:
            return

        p = self.current_player()
        if p.sid != sid:
            return

        p.finished = True
        self.next_turn()
        self.check_round_end()

    def hit(self, sid):
        if not self.started or self.match_winner or self.pending_actions:
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
            self.pending_actions.append({"action": "freeze", "sid": p.sid})
            return

        elif card.type == CardType.FLIP_3:
            self.pending_actions.append({"action": "flip3", "sid": p.sid})
            return
        
        elif card.type == CardType.DISCARD:
            anyNumberCards = any([len(elem.numbers) > 0 for elem in self.players])
            if anyNumberCards: # if no one has number cards to discard, act as no op
                # Step 1 DISCARD: the "choose target" phase (player who drew discard chooses self or another player)
                self.pending_actions.append({"action": "discard_choose_target", "sid": p.sid, "card_idx": len(p.cards)-1})
                return
        
        self.next_turn()
        self.check_round_end()

    def proceed_round(self):
        if self.pending_round_reset:
            self.start_new_round()
            self.pending_round_reset = False

    def apply_discard_choose_target(self, sid, target_sid, card_idx):
        # Validate request: only the player who drew the DISCARD can choose, and card_idx must match their most recent card
        for i in range(len(self.pending_actions)-1, -1, -1):
            a = self.pending_actions[i]
            if (
                a["action"] == "discard_choose_target"
                and a["sid"] == sid
                and a["card_idx"] == card_idx
            ):
                break
        else:
            return

        target = self.get_player_by_sid(target_sid)
        if not target or len(target.cards) == 0:
            self.pending_actions.pop(i)
            return

        # Remove the choose_target action; insert a pending action telling the target to choose what to discard
        self.pending_actions.pop(i)
        # Record target info into the discard card
        source = self.get_player_by_sid(sid)
        if source and len(source.cards) > card_idx:
            source.cards[card_idx].target = target.name if sid != target_sid else "(self)"
        # Step 2 DISCARD: the "choose card" phase
        self.pending_actions.append({"action": "discard_choose_card", "initiator_sid": sid, "target_sid": target_sid})
        return self.process_pending_actions()

    def apply_discard_choose_card(self, sid, card_idx):
        # This is called by the player who must choose a card to discard from own hand
        for i in range(len(self.pending_actions)-1, -1, -1):
            a = self.pending_actions[i]
            if (
                a["action"] == "discard_choose_card"
                and a["target_sid"] == sid
            ):
                break
        else:
            return

        target: Player = self.get_player_by_sid(sid)
        if not target or card_idx < 0 or card_idx >= len(target.cards):
            self.pending_actions.pop(i)
            return

        card_to_remove: Card = target.cards[card_idx]
        if card_to_remove.type == CardType.NUMBER:
            # Remove that card from the target's hand
            target.cards.pop(card_idx)
            target.numbers.remove(card_to_remove.value)

        self.pending_actions.pop(i)
        return self.process_pending_actions()

    def apply_flip3(self, sid, target_sid):
        # Find the last flip3 action
        for i in range(len(self.pending_actions)-1, -1, -1):
            a = self.pending_actions[i]
            if a["action"] == "flip3" and a["sid"] == sid:
                break
        else:
            return

        giver = self.get_player_by_sid(sid)
        target = self.get_player_by_sid(target_sid)

        if not giver or not target or target.finished:
            self.pending_actions.pop(i)
            return

        giver.cards[-1].target = target.name
        self.pending_actions.pop(i)  # Remove this flip3 action

        # Add a draw3 action for the target at the top of the stack
        self.pending_actions.append({
            "action": "draw3",
            "sid": target.sid,
            "remaining": 3
        })

        return self.process_pending_actions()

    def apply_freeze(self, sid, target_sid):
        # Find the last freeze targeting sid
        for i in range(len(self.pending_actions)-1, -1, -1):
            a = self.pending_actions[i]
            if a["action"] == "freeze" and a["sid"] == sid:
                break
        else:
            return

        target = self.get_player_by_sid(target_sid)
        if target.finished:
            return

        target.finished = True

        freezer = self.get_player_by_sid(sid)
        freezer.cards[-1].target = target.name

        self.pending_actions.pop(i)
        # Handle further pending actions:
        return self.process_pending_actions()

    def process_pending_actions(self):
        """Processes all pending actions, handling nested draw3/flip3/freeze."""
        # We'll return a list of game states
        game_states = []
        player_of_last_action = None
        while self.pending_actions:
            action = self.pending_actions[-1]
            if action["action"] == "draw3":
                player = self.get_player_by_sid(action["sid"])
                player_of_last_action = player
                if player.finished:
                    self.pending_actions.pop()
                    continue

                card = self.deck.draw()
                player.cards.append(card)

                if card.type == CardType.NUMBER:
                    if card.value in player.numbers:
                        if player.second_chance > 0:
                            player.second_chance -= 1
                        else:
                            player.busted = True
                            player.finished = True
                            self.pending_actions.pop()
                            game_states.append(self.to_dict())
                            break
                    else:
                        player.numbers.add(card.value)
                        if len(player.numbers) == 7:
                            player.flip7 = True
                            player.finished = True
                            self.pending_actions.pop()
                            game_states.append(self.to_dict())
                            break
                    action["remaining"] -= 1

                elif card.type == CardType.SECOND_CHANCE:
                    player.second_chance += 1
                    action["remaining"] -= 1

                elif card.type == CardType.FREEZE:
                    # Pause draw, push freeze
                    action["remaining"] -= 1
                    self.pending_actions.append({"action": "freeze", "sid": player.sid})
                    game_states.append(self.to_dict())
                    break

                elif card.type == CardType.FLIP_3:
                    # Pause draw, push flip3
                    action["remaining"] -= 1
                    self.pending_actions.append({"action": "flip3", "sid": player.sid})
                    game_states.append(self.to_dict())
                    break
                elif card.type == CardType.DISCARD:
                    # Pause draw, push discard and start from step 1 (choose target)
                    action["remaining"] -= 1
                    self.pending_actions.append({"action": "discard_choose_target", "sid": player.sid, "card_idx": len(player.cards)-1})
                    game_states.append(self.to_dict())
                    break

                game_states.append(self.to_dict())

                # Completed all 3 draws?
                if action["remaining"] <= 0:
                    self.pending_actions.pop()
            else:
                break  # Waiting for external choice (freeze/flip3/discard)
        
        if not self.pending_actions or (player_of_last_action is not None and player_of_last_action.finished):
            if player_of_last_action is not None and player_of_last_action.finished:
                self.pending_actions = []
            self.next_turn()
            self.check_round_end()
        return game_states

    def to_dict(self):
        pending_freeze = pending_flip3 = pending_discard_choose_target = pending_discard_choose_card = None
        discard_choose_target_info = {}
        discard_choose_card_info = {}
        for a in reversed(self.pending_actions):
            if not pending_freeze and a["action"] == "freeze":
                pending_freeze = a["sid"]
            if not pending_flip3 and a["action"] == "flip3":
                pending_flip3 = a["sid"]
            if not pending_discard_choose_target and a["action"] == "discard_choose_target":
                pending_discard_choose_target = a["sid"]
                discard_choose_target_info = {"card_idx": a["card_idx"]}
            if not pending_discard_choose_card and a["action"] == "discard_choose_card":
                pending_discard_choose_card = a["target_sid"]
                discard_choose_card_info = {"initiator_sid": a["initiator_sid"]}
        return {
            "code": self.code,
            "started": self.started,
            "round": self.round,
            "turn": self.turn,
            "pending_round_reset": self.pending_round_reset,
            "pending_freeze": pending_freeze,
            "pending_flip3": pending_flip3,
            "pending_discard_choose_target": pending_discard_choose_target,
            "discard_choose_target_info": discard_choose_target_info,
            "pending_discard_choose_card": pending_discard_choose_card,
            "discard_choose_card_info": discard_choose_card_info,
            "match_winner": self.match_winner.name if self.match_winner else None,
            "players": [p.to_dict() for p in self.players]
        }
