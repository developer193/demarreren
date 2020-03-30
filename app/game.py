import time
import logging
from random import shuffle
from app.errors import NotEnoughCardsError, WrongPlayerError

logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s: %(message)s')

logger.setLevel(logging.INFO)

RANKS = list(range(1, 14))
ACE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING = RANKS


class Card(object):
    def __init__(self, rank, suit):
        assert rank in RANKS
        self.rank = rank
        self.suit = suit
        self.name = str(rank)
        if rank == ACE:
            self.name = "ace"
        elif rank == JACK:
            self.name = "jack"
        elif rank == QUEEN:
            self.name = "queen"
        elif rank == KING:
            self.name = "king"
        self.shorthand = self.name if self.name.isdigit() else self.name[0]

    def __str__(self):
        return f"{self.name} of {self.suit}"


class Player(object):
    def __init__(self, name: str, player_id: str, hand: list = None):
        self.name = name
        self.player_id = player_id
        self.hand = hand if hand else []
        self.sips_taken = 0
        self.drinks_taken = 0
        self.sips_given = 0
        self.drinks_given = 0

    def play_card(self, card, game):
        ok, _, error = game.move(player=self, card=card)
        if ok:
            self.hand.remove(card)
            game.wastepile.append(card)
            if game.count != 0:
                if game.count % 10 == 0:
                    self.hand_out_sip()
                elif game.count % 11 == 0:
                    self.take_sip()

    def pick_card(self, game) -> tuple:
        """
        Pick a card from the stock
        returns (ok, object, error)
        """
        if not game.stock:
            return False, self, NotEnoughCardsError
        card = game.stock.pop(0)
        self.hand.append(card)
        return True, self, None

    def shuffle_cards(self, game):
        """Add discarded cards and shuffle stock"""
        logger.info("shuffling cars")
        game.stock += game.wastepile[:-1]
        game.wastepile = game.wastepile[-1]
        shuffle(game.stock)

    def take_sip(self, n_sips=1):
        logger.info(f"{self.name} takes {n_sips} sip{'s' if n_sips > 1 else ''}")
        self.sips_taken += n_sips

    def take_drink(self):
        logger.info(f"{self.name} downs his drink")
        self.drinks_taken += 1

    def hand_out_sip(self, player=None, n_sips=1):
        logger.info(f"{self.name} gives out {n_sips} sip{'s' if n_sips > 1 else ''}")
        self.sips_given += n_sips
        if player:
            player.sips_taken += n_sips

    def hand_out_drink(self, player=None):
        logger.info(f"{self.name} gives out a drink")
        self.drinks_given += 1
        if player:
            player.drinks_taken += 1

    def pick_value(self, options: list) -> int:
        """Needs to be overridden for non-cli use"""
        value: int = 0
        while value not in options:
            try:
                value = int(input(f"which value? {options}: "))
            except ValueError:
                pass
        return value


class Game(object):
    def __init__(self, stock: list, rules=None, players: list = None):
        self.rules = rules
        self.stock: list = stock
        self.wastepile: list = []
        self.count: int = 0
        self.players: list = []
        self.direction: 1 or -1 = 1
        if players:
            for player in players:
                self.add_player(player)
        self.current_player: Player = self.players[0] if self.players else None
        shuffle(self.stock)

    def add_player(self, player) -> tuple:
        """
        Add a player and give him his cards
        returns (ok, object, error)
        """
        n_cards = 4
        if not len(self.stock) >= n_cards:
            return False, player, NotEnoughCardsError
        for _ in range(n_cards):
            player.pick_card(self)

        self.players.append(player)
        if not self.current_player:
            self.current_player = player
        return True, player, None

    def move(self, player, card) -> tuple:
        """
        Game action takes place
        returns (ok, object, error)
        """
        if self.current_player.player_id != player.player_id:
            return False, self, WrongPlayerError
        self.wastepile.append(card)
        if card.rank == ACE:
            value = player.pick_value([1, 11])
            self.count += value
        elif card.rank <= NINE:
            self.count += card.rank
        elif card.rank == TEN:
            value = player.pick_value([-10, 10])
            self.count += value
        elif card.rank == JACK:
            self.count = 96
        elif card.rank == QUEEN:
            pass
        elif card.rank == KING:
            self.direction = -1 if self.direction == 1 else 1
        if self.count >= 100:
            self.game_over(player)
        else:
            self.next_player()
        return True, self, None

    def next_player(self):
        """Set the current_player value"""
        current_index = self.players.index(self.current_player)
        unsafe_index = current_index + self.direction  # can be OutOfIndex
        index = unsafe_index % len(self.players)  # cycle index
        self.current_player = self.players[index]


    def game_over(self, player):
        logger.info(f"{player.name} lost")
        player.take_drink()
        overshot = self.count - 100
        if overshot > 0 and overshot % 10 == 0:
            for _ in range(overshot//10):
                player.hand_out_drink()
        self.count = 0


def get_deck(n_decks: int = 1) -> list:
    """Returns 52 Cards * n_decks"""
    suits = ["spades", "hearts", "diamonds", "clubs"]
    deck = []
    for _ in range(n_decks):
        for suit in suits:
            for rank in RANKS:
                deck.append(Card(rank=rank, suit=suit))
    return deck

def print_game(game, count: bool = True, stock = True, turn: bool = True, hands: bool = True):
    if count:
        print(f"the count is {game.count}")
    if stock:
        print(f"{len(game.stock)} cards left")
    if turn and game.current_player:
        print(f"{game.current_player.name} to play")
    if hands:
        for player in game.players:
            print(f"    {player.name}: {player.hand}")


def cli():
    deck = get_deck()
    game = Game(stock=deck)
    players_input = input("type player names separated by comma: ").split(',')
    for i in range(len(players_input)):
        name = players_input[i].strip()
        game.add_player(Player(name=name, player_id=str(i)))
    while True:
        time.sleep(1)
        print('-' * 80)
        print_game(game, hands=False)
        print('-' * 80)
        player = game.current_player
        options = [(player.hand[i].shorthand, player.hand[i]) for i in range(len(player.hand))]
        print('\t' + '\n\t'.join([f"{value[0]} ({value[1]})" for value in options]))
        game_input = None
        while game_input not in [value[0] for value in options]:
            time.sleep(1)
            game_input = input(f"what will {player.name} play?: ")
        player.play_card([value[1] for value in options if value[0] == game_input][0], game)
        player.pick_card(game)


if __name__ == "__main__":
    cli()
