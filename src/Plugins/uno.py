import random
import time
from collections import defaultdict

class Plugin:
	#active = False

	#modes
	INACTIVE = 0
	JOINING = 1
	PLAYING = 2

	#player direction
	FORWARD = 1
	BACKWARD = -1

	def __init__(self, controller):
		self.c = controller

		self.uno = "\002\0034U\0033N\0032O\0038!\003\002"

		#create full deck
		self.full_deck = [colour+card for colour in 'rgby' for card in '123456789RSD'*2+'0']
		self.full_deck += ['wW', 'wW4']*4

		self.deck = []
		self.hands = defaultdict(list)
		self.discard = []

		self.timer = 0
		self.mode = self.INACTIVE
		self.turn = 0

		self.current_player = 0
		self.players = []
		self.start_player = ''
		self.channel = ''

		self.direction = self.FORWARD
		self._skip = 0
		self.force_colour = False
		self.topcolour = ''
		self.topnumber = -1


	def help(self, msg):
		pass

	def trigger_uno(self, msg):
		"\002\0034U\0033N\0032O\0038!\003:\002 Uno for IRC. For detailed help, run `uno help`"

		if len(msg.args) == 0:
			self.c.notice(msg.nick, "Please specify an UNO command. Check `%suno help` for avaliable commands."%self.c.plugins.prefix)
			return

		command = msg.args.pop(0)
		if command in dir(self) and not command.startswith('_'):
			getattr(self, command)(msg)
		else:
			self.c.notice(msg.nick, "The command '%s' does not exist. Check `%suno help` for avalable commands."%(command, self.c.plugins.prefix))

	def start(self, msg):
		# Can't-play conditions...
		if not self.timer == 0 and not self.mode:
			self.c.notice(msg.nick, "%s is on cooldown. %s minutes to go..."%(self.uno, self.timer))
			return
		if self.mode:
			self.c.notice(msg.nick, "There is already a game of %s running!"%self.uno)
			return

		self.mode = self.JOINING
		self.start_player = msg.nick
		self.channel = msg.channel
		self.c.privmsg(self.channel, "New game of %s starting! Type `%suno join` to join the fun! Game will start in about 2 minutes..."%(self.uno, self.c.plugins.prefix))
		self.join(msg)
		self.timer = 2

	def stop(self, msg):
		if not (self.c.is_admin(msg.nick) or msg.nick == self.start_player):
			self.c.notice(msg.nick, "Only bot admins and the start player can stop a game.")
			return
		elif self.mode == self.INACTIVE:
			self.c.notice(msg.nick, "There is no game of %s in progress."%self.uno)
			return

		self._reset()

	def join(self, msg):
		if msg.channel != self.channel:
			self.c.notice(msg.nick, "Please join %s to join the game of %s."%(self.channel, self.uno))
			return
		elif msg.nick in self.players:
			self.c.notice(msg.nick, "You've already joined the game!")
			return
		elif len(self.players) == 10:
			self.c.notice(msg.nick, "The current game of %s is full, sorry."%self.uno)
			return
		elif self.mode == self.INACTIVE:
			self.c.notice(msg.nick, 'There is no %s game running! Why not start one with `%suno start`?'%(self.uno, self.c.plugins.prefix))
			return
		elif self.mode == self.PLAYING:
			self.c.notice(msg.nick, "There's already a game of %s running!"%self.uno)
			return

		self.players.append(msg.nick)
		self.c.privmsg(self.channel, "%s has joined the game!"%msg.nick)
		if len(self.players) == 10:
			self.c.privmsg(self.channel, "The game is full! Get ready to play %s!"%self.uno)

	def leave(self, msg):
		if self.mode == self.PLAYING:
			self.c.notice(msg.nick, "You can't leave during a game!")
			return
		elif msg.nick not in self.players:
			self.c.notice(msg.nick, "You can't leave something you havn't joined!")
			return

		self.players.remove(msg.nick)
		self.c.privmsg(self.channel, "%s has left the game."%msg.nick)

	CARD_MAP = {
		'draw':'D',
		'skip':'S',
		'reverse':'R',
		'wild':'W',
		'wild4':'W4',
		'wildfour':'W4',
		'red':'r',
		'green':'g',
		'blue':'b',
		'yellow':'y'
	}
	NAME_MAP =  {
		'W':'Wild',
		'W4':'Wild Draw Four',
		'R':'Reverse',
		'S':'Skip',
		'D':'Draw Two',
		'r':'Red',
		'g':'Green',
		'b':'Blue',
		'y':'Yellow'
	}
	def play(self, msg):
		if not self.mode == self.PLAYING:
			self.c.notice(msg.nick, "There's no game of %s currently in progress!"%uself.uno)
			return
		if not self.players[self.current_player] == msg.nick:
			self.c.notice(msg.nick, "It's not your turn!")
			return
		colour = msg.args.pop(0).lower()
		try: colour = self.CARD_MAP[colour]
		except KeyError: pass
		if colour not in 'rgby':
			self.c.notice(msg.nick, "Invalid colour specified.")
			return
		if self.force_colour and colour != self.topcolour:
			if self.turn != 1:
				self.c.notice(msg.nick, "You must place a %s card, or pick up."%self.NAME_MAP[self.topcolour])
				return
		elif self.force_colour:
			self.force_colour = False

		ctype = "".join(msg.args).lower()
		try: ctype = self.CARD_MAP[ctype]
		except KeyError: pass
		ctype = ctype.upper()
		if ctype not in 'RSDW4012356789':
			self.c.notice(msg.nick, "Invalid card type specified.")
			return

		card = ('w' if (ctype == 'W' or ctype == 'W4') else colour)+ctype
		if card not in self.hands[msg.nick]:
			self.c.notice(msg.nick, "You do not have that card")
			return

		if not (ctype == self.topnumber or colour == self.topcolour or 'W' in ctype):
			self.c.notice(msg.nick, "That card cannot be placed.")
			return

		if ctype == 'W4' and colour in [i[0] for i in self.hands[msg.nick]]:
			self.c.notice(msg.nick, "Wild Draw Four cards can only be placed when you do not have a card the same colour as the pile.")
			return

		self.hands[msg.nick].remove(card)

		card = colour+ctype
		try: lname = self.NAME_MAP[ctype]
		except KeyError: lname = ctype
		self.c.privmsg(self.channel, "%s plays a %s %s."%(msg.nick, self.NAME_MAP[colour], lname))

		cards_left = len(self.hands[msg.nick])
		if cards_left == 1:
			self.c.privmsg(self.channel, "%s %s has 1 card remaining!"%(self.uno, msg.nick))
		elif cards_left == 0:
			self.c.privmsg(self.channel, "%s is out of cards! WINNER!~"%msg.nick)
			self._reset()
			return

		self._do_action(card)
		self._discard(card)
		self._begin_turn()

	def hand(self, msg):
		if not msg.nick in self.players:
			self.c.notice(msg.nick, "You are not playing!")
			return

		self.c.notice(msg.nick, "Your hand: %s"%self._render_hand(player))

	def pickup(self, msg):
		if not self.players[self.current_player] == msg.nick:
			self.c.notice(msg.nick, "It's not your turn!")
			return
		self._draw_card(msg.nick)
		self._begin_turn()

	def timer_60(self):
		if self.timer > 1:
			self.timer -= 1

			if self.mode == self.JOINING:
				self.c.privmsg(self.channel, "%s game will begin in 1 minute!"%self.uno)

			elif self.mode == self.INACTIVE:
				if self.timer == 5 or self.timer == 1:
					self.c.privmsg(self.channel, "%s cooldown: %s minute%s remaining."%(self.uno, self.timer, 's' if self.timer > 1 else ''))
		else:
			self.timer = 0

			if self.mode == self.JOINING:
				self._begin()

	def skip(self, msg):
		if not (self.c.is_admin(msg.nick) or msg.nick == self.start_player):
			self.c.notice(msg.nick, "Only bot admins and the start player can stop a game.")
			return
		if self.mode != self.JOINING:
			self.c.notice(msg.nick, "This command can only be used in the player signup stage.")
		self.timer = 0
		self._begin()

	def _begin(self):
		if len(self.players) < 2:
			self.c.privmsg(self.channel, "%s needs at least 2 people to play! Game halted.")
			self._reset(False)
			return
		self.mode = self.PLAYING
		self._set_up()



#### The game starts here! ####
# (all that stuff above is player management and stuff)
	def _reset(self, CD=True):
		self.players = []
		self.start_player = ''
		self.mode = self.INACTIVE
		self.turn = 0
		if CD:
			self.timer = 10
			self.c.privmsg(self.channel, "%s game finished. Hope you had fun! Uno can be played again in about 10 minutes." % (self.uno))

	# Set up the game!
	def _set_up(self):
		#shuffe the cards and the player order (man python makes one's life easy :D)
		random.shuffle(self.players)
		self.deck = self.full_deck[:]
		random.shuffle(self.deck)

		self.c.privmsg(self.channel, "%s is dealing."%self.players[self.current_player])

		#Deal the cards. Gotta keep it going 'round the table, it's how it works!
		self.hands = defaultdict(list)
		for player in self.players*7: #7 cards each
			self._draw_card(player, silent=True)

		#Start the discard pile
		self.c.privmsg(self.channel, "Flipping the top card...")
		discard = self.deck.pop()
		while discard == 'wW4': #first card can't be a Wild D4
			self.c.privmsg(self.channel, "It was a \002Wild Draw Four\002. Flipping next card.")
			self.deck.insert(random.randint(0, len(self.deck)), 'wW4')
			discard = self.deck.pop()
		self._discard(discard)

		self._do_action(self.discard[-1])

		self._begin_turn()

	def _discard(self, card):
		self.discard.append(card)
		self.topcolour = card[0]
		self.topnumber = card[1:]

	def _begin_turn(self):
		self._next_player()
		while self._skip > 0:
			self._skip -= 1
			self.c.privmsg(self.channel, "%s's turn was skipped."%self.players[self.current_player])
			self._next_player()

		self.turn += 1
		player = self.players[self.current_player]
		self.c.privmsg(self.channel, "Turn %s: %s's turn."%(self.turn, player))
		self.c.privmsg(self.channel, "Top card: %s"%self._render_card(self.discard[-1]))
		self.c.notice(player, "Your hand: %s"%self._render_hand(player))

	def _next_player(self, get=False):
		if get: temp = self.current_player
		self.current_player += self.direction
		if self.current_player < 0:
			self.current_player += len(self.players)
		elif self.current_player >= len(self.players):
			self.current_player -= len(self.players)
		if get:
			num = self.current_player
			self.current_player = temp
			return num


	def _do_action(self, card):
		card_type = card[1:]
		if card_type == 'R':
			if len(self.players) == 2:
				self._skip = 1
			else:
				self.direction = -self.direction
				self.c.privmsg(self.channel, "Direction of play was reversed!")
		elif card_type == 'S':
			self._skip = 1
		elif card_type == 'D':
			self._draw_card(self.players[self._next_player(True)], 2)
			self._skip = 1
		elif card_type == 'W':
			self.force_colour = True
		elif card_type == 'W4':
			self._draw_card(self.players[self._next_player(True)], 4)
			self.force_colour = True
			self._skip = 1

	def _draw_card(self, player, number=1, silent=False):
		if not silent: self.c.privmsg(self.channel, "%s draws %s card%s."%(player, number, 's' if number>1 else ''))
		for i in range(number):
			if len(self.deck) == 0:
				self.deck = self.discard[:-1]
				random.shuffle(self.deck)
				self.c.privmsg(self.channel, "Discard pile shuffled and added to deck.")
			self.hands[player].append(self.deck.pop())

	def _render_hand(self, player):
		out = ''
		for card in sorted(self.hands[player]):
			out += self._render_card(card)
		return out
		
	COLOUR_MAP = {
		'r':'00,04',
		'g':'00,03',
		'b':'00,02',
		'y':'01,08',
		'w':'00,01'
	}
	def _render_card(self, card):
		return '\003%s\002[%s]\002\003'%(self.COLOUR_MAP[card[0]],card[1:])

