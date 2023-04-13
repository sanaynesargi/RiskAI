import time
import random
from math import sqrt, log, comb

import pygame
import operator
import math
import numpy as np
from ast import literal_eval as tuple_from_string
from copy import deepcopy

from Tree import Tree, TreeNode, _pretty_print_data
from card_maps import territory_attack_map, risk_cards
from troop import Troop
from itertools import product


def create_location_troop_coordinates():
    troop_locations = {}

    location_file = open("locations.txt")
    locations = location_file.read().split("\n")
    location_file.close()

    with open("territories.txt", "r") as territories:
        start = 0
        stop = 3
        for territory in territories.read().split("\n"):
            if len(territory) == 0:
                continue

            troop_locations[territory] = [tuple_from_string(x) for x in locations[start:stop + 1]]
            start = stop + 1
            stop += 4

    return troop_locations


# [Red, Light Blue, Green, Black] ---> Order for referencing colors
def get_color_index(color):
    return ["Red", "Light Blue", "Green", "Black"].index(color)


def get_color_by_index(index):
    return ["Red", "Light Blue", "Green", "Black"][index]


def simulate_dice_roll():
    return random.randint(1, 6)


def simulate_attack(attacking_armies, defending_armies, max_rounds=10):
    remaining_attacking_armies = attacking_armies
    remaining_defending_armies = defending_armies

    for i in range(max_rounds):
        # Stop simulating if the attacking territory cannot attack anymore
        if remaining_attacking_armies <= 1:
            break

        # Stop simulating if the defending territory is captured
        if remaining_defending_armies <= 0:
            break

        # Attacker rolls up to three dice
        attack_dice = sorted([random.randint(1, 6) for _ in range(min(3, remaining_attacking_armies - 1))],
                             reverse=True)

        # Defender rolls up to two dice
        defense_dice = sorted([random.randint(1, 6) for _ in range(min(2, remaining_defending_armies))], reverse=True)

        # Compare each pair of dice
        for j in range(min(len(attack_dice), len(defense_dice))):
            if attack_dice[j] > defense_dice[j]:
                # Attacker wins, defender loses one army
                remaining_defending_armies -= 1
            else:
                # Defender wins, attacker loses one army
                remaining_attacking_armies -= 1

    # Estimate the win probability based on the number of remaining armies
    if remaining_defending_armies <= 0:
        win_probability = 1.0
    else:
        win_probability = float(remaining_attacking_armies - 1) / float(attacking_armies)

    return win_probability


def calculate_attack_success_probability(attack_armies, defence_armies):
    total = 100000
    success = 0
    for _ in range(total):
        result = simulate_attack(attack_armies, defence_armies)
        if result:
            success += 1

    return success / total


def find_owner_of_territory_in_gamestate(territory, territories_in_gs):
    for color, territories in territories_in_gs.items():
        if territory in territories:
            return color

    return None


def allocate_troops(total_troops, territory_dict):
    num_territories = len(territory_dict)
    if total_troops <= 0 or num_territories == 0:
        return {}

    troops_per_territory = total_troops // num_territories
    extra_troops = total_troops % num_territories
    allocated = {}

    for territory, troops in territory_dict.items():
        allocated[territory] = troops_per_territory
        if extra_troops > 0:
            allocated[territory] += 1
            extra_troops -= 1

    while extra_troops < 0:
        # remove troops from the territory with the most troops
        max_troops = -math.inf
        max_territory = None
        for territory, troops in allocated.items():
            if troops > max_troops:
                max_troops = troops
                max_territory = territory
        allocated[max_territory] -= 1
        extra_troops += 1

    return allocated


def allocate_troops_by_attacks(attacks, total_troops):
    allocated = {}
    remaining_troops = total_troops

    sorted_attacks = sorted(attacks.items(), key=lambda x: x[1], reverse=True)

    for territory, num_attacks in sorted_attacks:
        if remaining_troops <= 0:
            break
        num_troops = min(remaining_troops, num_attacks + 1)
        allocated[territory] = num_troops
        remaining_troops -= num_troops

    for territory, num_attacks in sorted_attacks:
        if remaining_troops <= 0:
            break
        if territory not in allocated:
            num_troops = min(remaining_troops, num_attacks + 1)
            allocated[territory] = num_troops
            remaining_troops -= num_troops

    if remaining_troops > 0:
        print("Warning: Not enough troops to allocate to all territories")

    return allocated


def allocate_fortification_troops(full_map, map_dict, source_territory, num_troops):
    """
    Allocates `num_troops` troops from neighboring territories to the `source_territory` in a way that
    tries to equalize troop distribution among neighbors. Each neighboring territory will be required
    to move at least 1 troop, and `source_territory` will be required to keep at least 2 troops.

    Args:
    - map_dict (dict): A dictionary representing the game map
    - source_territory (str): The name of the territory to allocate troops to
    - num_troops (int): The number of troops to allocate to the `source_territory`

    Returns:
    - allocation_dict (dict): A dictionary indicating how many troops each neighboring territory
                              should move to the `source_territory`
    """
    # Create a dictionary to store the number of troops for each territory
    troops_dict = {territory: full_map[territory]['troops'] for territory in full_map}

    # Get a list of the `source_territory`'s neighbors and sort them by the number of troops they have
    neighbors = sorted(map_dict[source_territory]['neighbors'], key=lambda x: troops_dict[x])

    # Compute the total number of troops among neighbors
    total_troops = sum(troops_dict[neighbor] for neighbor in neighbors)

    # Calculate how many troops each neighbor should contribute, rounded down to the nearest integer
    allocations = {}
    for neighbor in neighbors:
        allocation = min(max(1, round(num_troops * troops_dict[neighbor] / total_troops)), troops_dict[neighbor] - 1)
        allocations[neighbor] = allocation

    return allocations


def backpropagate(node, reward, total):
    # Update the statistics of the current node
    node.num_visits += total
    node.reward += reward
    # Recursively update the statistics of the parent nodes
    if node.parent is not None:
        backpropagate(node.parent, reward, total)


def get_key_territories():
    return [
        "Indonesia",  # Key territory to control Southeast Asia and Oceania
        "Venezuela",  # Connects South America with Central America, easy to defend choke point
        "North Africa",  # Good starting point for expansion into Europe or Africa
        "Middle East",  # Connects Asia with Africa and Europe, easy to defend choke point
        "Ukraine",  # Connects Europe with Asia, key territory for control of the continent
        "China",  # Large territory with multiple borders, key territory to control Asia
        "India",  # Connects Asia with the Middle East, easy to defend choke point
        "Western Europe",  # Good starting point for expansion into other parts of Europe
        "Eastern United States",  # Good starting point for expansion into North and South America
        "Brazil",  # Connects South America with Africa and Europe, key territory for control of the continent
    ]


class RiskGame:
    PLAYER = 0
    TURNS_PLAYED = 0
    PICK_TERRITORIES_MODE = True
    DRAW = True
    ATTACK_MODE = False
    TERRITORIES_REMAINING_COUNT = {"Red": 30, "Light Blue": 30, "Green": 30, "Black": 30}
    TERRITORIES_OWNED = {"Red": [], "Light Blue": [], "Green": [], "Black": []}
    CARDS_OWNED = {"Red": [], "Light Blue": [], "Green": [], "Black": []}
    MATCHES_MADE = 0

    def __init__(self, surface, background, update_ui_callback):
        self._territory_file_path = "territories.txt"
        self.surface = surface
        self._location_troop_coordinates = create_location_troop_coordinates()

        self._troops_on_board = self._create_territory_troop_map()

        self.imported_cards = deepcopy(risk_cards)
        self.territory_attack_map = deepcopy(territory_attack_map)

        self.CARDS = self._create_card_deck()
        self.TERRITORIES_REMAINING = self._get_all_territories()
        self.TERRITORY_ATTACK_COUNT = {t: 0 for t in self._get_all_territories()}
        self.BACKGROUND = background

        self.ui_callback = update_ui_callback

        random.shuffle(self.CARDS)

    def _create_territory_troop_map(self):
        troop_map = {}
        with open(self._territory_file_path, "r") as data:
            for territory in data.read().split("\n"):
                if len(territory) == 0:
                    continue

                coordinates = self._location_troop_coordinates[territory]
                troops_created = []
                for index, coordinate in enumerate(coordinates):
                    color = get_color_by_index(index)
                    troops_created.append(Troop(self.surface, color, coordinate, number=0))
                troop_map[territory] = troops_created

        return troop_map

    def _get_all_territories(self):
        territories = []
        with open(self._territory_file_path, "r") as data:
            for territory in data.read().split("\n"):
                if len(territory) == 0:
                    continue
                territories.append(territory)

        return territories

    def _create_card_deck(self):
        deck = []
        for card in self.imported_cards:
            for _ in range(card[2]):
                deck.append((card[0], card[1]))

        return deck

    def send_troops(self, color, territory, number):
        color_index = get_color_index(color)
        self._troops_on_board[territory][color_index].number += number

    def change_turn(self):
        if self.PLAYER == 3:
            self.PLAYER = 0
            return

        self.PLAYER += 1
        self.TURNS_PLAYED += 1

        if self.DRAW:
            self.draw()

    def _select_territory(self, color, choices):
        while True:
            territory = random.choice(choices)
            territory_not_contained = True

            for c in self.TERRITORIES_OWNED.keys():
                if territory in self.TERRITORIES_OWNED[c]:
                    territory_not_contained = False
                    break

            if territory_not_contained:
                return territory

    def _get_continent_owned_bonus(self, color, territories_in_gs):
        if territories_in_gs is None:
            territories_in_gs = self.TERRITORIES_OWNED

        bonus = 0
        troop_bonuses = {"NA": 5, "SA": 2, "EU": 5, "AF": 3, "AS": 7, "AU": 2}
        territories_by_continent = {
            "NA": ["Alaska", "Northwest Territory", "Greenland", "Alberta", "Ontario", "Quebec",
                   "Western United States", "Eastern United States", "Central America"],
            "SA": ["Venezuela", "Peru", "Brazil", "Argentina"],
            "EU": ["Iceland", "Scandinavia", "Ukraine", "Great Britain", "Northern Europe", "Southern Europe",
                   "Western Europe"],
            "AF": ["North Africa", "Egypt", "East Africa", "Congo", "South Africa", "Madagascar"],
            "AS": ["Ural", "Siberia", "Yakutsk", "Kamchatka", "Afghanistan", "Middle East", "India", "China",
                   "Mongolia", "Japan", "Irkutsk", "Kazakhstan", "Siam"],
            "AU": ["Indonesia", "New Guinea", "Western Australia", "Eastern Australia"]
        }

        for continent, territories in territories_by_continent.items():
            if territories in territories_in_gs[color]:
                bonus += troop_bonuses[continent]

        return bonus

    def _get_card_trade_bonus(self, color, territories_in_gs):

        if territories_in_gs is None:
            territories_in_gs = self.TERRITORIES_OWNED

        bonus = 0

        cards_owned = self.CARDS_OWNED[color]

        cards_found = []
        card_types = ["Artillery", "Infantry", "Cavalry", "Wild"]
        wild_card_used = False
        territory_bonus_1 = 0
        match_cards_1 = []

        if len(self.CARDS_OWNED[color]) < 3:
            return 0

        for t in card_types:
            best_card = ""
            for card in cards_owned:
                if card[1] != t:
                    continue
                if len(cards_found) == 3:
                    break

                if card[0] in territories_in_gs[color]:
                    best_card = card
                    break
                elif card[1] == "Wild" and not wild_card_used:
                    best_card = card
                    break
                elif card != "Wild":
                    best_card = card

            if best_card != "":
                if best_card[1] == "Wild" and not wild_card_used:
                    cards_found.append(best_card)
                    wild_card_used = True
                elif best_card[1] != "Wild":
                    cards_found.append(best_card)

        different_cards_bonus = len(cards_found) == 3

        if different_cards_bonus:
            for card in cards_found:
                if card[0] in territories_in_gs[color]:
                    territory_bonus_1 = 2
                    match_cards_1 = cards_found
                    break

        territory_bonus_2 = 0
        types = {"Artillery": [], "Cavalry": [], "Infantry": []}
        wild_card_used = False
        match_cards_2 = []

        for card in cards_owned:
            if card[1] == "Wild" and not wild_card_used:
                types["Artillery"].append(".")
                types["Infantry"].append(".")
                types["Cavalry"].append(".")
                wild_card_used = True
                continue
            elif card[1] == "Wild":
                continue

            types[card[1]].append(card[0])

        same_card_type_bonus = len(types["Artillery"]) == 3 or len(types["Infantry"]) == 3 or len(types["Cavalry"]) == 3
        if same_card_type_bonus:
            for _, cards in types.items():
                if len(cards) != 3:
                    continue

                match_cards_2.clear()
                for card in cards:
                    if card in territories_in_gs[color]:
                        territory_bonus_2 += 2
                        match_cards_2 = cards
                        break

        if not same_card_type_bonus and not different_cards_bonus:
            return 0

        total_territory_bonus = territory_bonus_1 + territory_bonus_2
        matched_cards_to_remove = []

        if same_card_type_bonus and not different_cards_bonus:
            matched_cards_to_remove = match_cards_1
        elif different_cards_bonus and not same_card_type_bonus:
            matched_cards_to_remove = match_cards_2
        else:
            if territory_bonus_1:
                matched_cards_to_remove = match_cards_1
            elif territory_bonus_2:
                matched_cards_to_remove = match_cards_2
            else:
                matched_cards_to_remove = match_cards_2

        if total_territory_bonus > 2:
            total_territory_bonus = 2

        if self.MATCHES_MADE == 0:
            bonus = 4
        elif self.MATCHES_MADE == 1:
            bonus = 6
        elif self.MATCHES_MADE == 2:
            bonus = 8
        elif self.MATCHES_MADE == 3:
            bonus = 10
        elif self.MATCHES_MADE >= 4:
            bonus = 12

        self.MATCHES_MADE += 1

        # add cards to back of deck
        random.shuffle(matched_cards_to_remove)  # shuffle cards before adding them back
        for card in matched_cards_to_remove:
            self.CARDS_OWNED[color].remove(card)
            self.CARDS.append(card)

        return min(12, bonus + total_territory_bonus)

    def _draw_card(self, color):
        if len(self.CARDS) == 0:
            self.CARDS = self._create_card_deck()
            random.shuffle(self.CARDS)

        card = self.CARDS[0]

        del self.CARDS[0]

        self.CARDS_OWNED[color].append(card)

    def _place_troops_before_attack(self, color, troop_count):

        territories_to_place = random.choices(self.TERRITORIES_OWNED[color], k=troop_count)

        while troop_count > 0:
            for territory in territories_to_place:
                troops_to_place = random.randint(1, len(territories_to_place))
                color_index = get_color_index(color)

                troop = self._troops_on_board[territory][color_index]
                troop.number += troops_to_place
                troop.highlight = True

                troop_count -= troops_to_place

    def _kill_highlights(self, color):
        for troops in self._troops_on_board.values():
            for troop in troops:
                troop.highlight = False
                troop.arrow = False
                troop.highlight_attack = False
                troop.highlight_defend = False

    def _find_owner_of_territory(self, territory):
        for color, territories in self.TERRITORIES_OWNED.items():
            if territory in territories:
                return color

        return None

    def _run_attack_sequence(self, attack_color, defence_color, territory_attacking, territory_defending):
        attack_color_index = get_color_index(attack_color)
        defence_color_index = get_color_index(defence_color)

        attack_troop = self._troops_on_board[territory_attacking][attack_color_index]
        defending_troop = self._troops_on_board[territory_defending][defence_color_index]

        attack_troop.highlight_attack = True
        attack_troop.arrow = True
        defending_troop.highlight_defend = True
        defending_troop.arrow = True

        max_attack_dice_rolls = min(attack_troop.number - 1, 3)
        max_defence_dice_rolls = min(defending_troop.number, 2)

        attack_dice_rolls = random.randint(1, max_attack_dice_rolls) if max_attack_dice_rolls != 1 else 1

        if max_defence_dice_rolls == 0:
            print(
                f"ATTACK SUCCESS. ATTACKER: {attack_color} DEFENDER: {defence_color}  {territory_attacking} vs. "
                f"{territory_defending} DEFENDER LOSES 0 TROOPS")

            self.TERRITORIES_OWNED[defence_color].remove(territory_defending)
            self.TERRITORIES_OWNED[attack_color].append(territory_defending)

            defending_troop.color = attack_color
            defending_troop.number = attack_dice_rolls

            print(f"CLAIM ALERT: ATTACKER: {attack_color} claimed {territory_defending}")
            return 1

        defence_dice_rolls = random.randint(1, max_defence_dice_rolls) if max_defence_dice_rolls != 1 else 1

        attack_dice_results = sorted([simulate_dice_roll() for _ in range(attack_dice_rolls)], reverse=True)
        defence_dice_results = sorted([simulate_dice_roll() for _ in range(defence_dice_rolls)], reverse=True)

        attack_wins = 0
        defence_wins = 0

        for attack_roll, defence_roll in zip(attack_dice_results, defence_dice_results):
            if attack_roll > defence_roll:
                attack_wins += 1
            else:
                defence_wins += 1

        if attack_wins > defence_wins:
            pre_attack = defending_troop.number
            defending_troop.number = max(0, pre_attack - attack_wins)
            print(
                f"ATTACK SUCCESS. ATTACKER: {attack_color} DEFENDER: {defence_color}  {territory_attacking} vs. "
                f"{territory_defending} DEFENDER LOSES {attack_wins} TROOPS")

            if defending_troop.number == 0:
                self.TERRITORIES_OWNED[defence_color].remove(territory_defending)
                self.TERRITORIES_OWNED[attack_color].append(territory_defending)

                defending_troop.color = attack_color
                defending_troop.number = attack_wins
                self._troops_on_board[territory_attacking][attack_color_index].number -= attack_wins
                print(f"CLAIM ALERT: ATTACKER: {attack_color} claimed {territory_defending}")

            return 1
        else:
            pre_attack = attack_troop.number
            attack_troop.number = max(0, pre_attack - defence_wins)

            print(
                f"DEFENCE SUCCESS. ATTACKER: {attack_color} DEFENDER: {defence_color}  {territory_attacking} vs. "
                f"{territory_defending} ATTACKER LOSES {defence_wins} TROOPS")

            return 0

    def _attack(self, color):
        attackable_territories = []
        color_index = get_color_index(color)

        for territory in self.TERRITORIES_OWNED[color]:
            neighbors = self.territory_attack_map[territory]

            if self._troops_on_board[territory][color_index].number < 2:
                continue

            for neighbor in neighbors:
                attackable_territories.append((neighbor, territory))

        while True:
            territory_to_attack, territory_attacking = random.choice(attackable_territories)
            opposing_color = self._find_owner_of_territory(territory_to_attack)

            if self._troops_on_board[territory_attacking][color_index].number < 2:
                territory_to_attack, territory_attacking = random.choice(attackable_territories)
                opposing_color = self._find_owner_of_territory(territory_to_attack)
                continue

            result = self._run_attack_sequence(color, opposing_color, territory_attacking, territory_to_attack)
            self.draw()
            time.sleep(1)
            self._kill_highlights(color)

            if result == 0:
                break

    def _fortify_territory(self, t1, t2, troops):
        if t2 not in self.territory_attack_map[t1]:
            return

        territory_number = self._get_troop_count_from_territory(t2)

        if troops > territory_number - 1:
            return

        troop = self._get_troop_from_territory(t1)
        troop2 = self._get_troop_from_territory(t2)

        troop.number += troops
        troop2.number -= troops

    def _ucb(self, color, child, node, N, n):
        c = 1.5
        X = self.evaluate_game_state(child[1].data[1], child[1].data[0], color)

        # default UCB value
        if N == 0:
            return X + c * sqrt(log(1) / n)

        return X + c * sqrt(log(N) / n)

    def _simulate_game(self, color, node):
        wins, total = 0, 0
        while not node.is_terminal(color):
            # Select a random child
            child = random.choice(node.children)
            child = child[1]
            # Check if the child has any children, and treat it as a terminal state if it does not
            if not child.children:
                if child.is_winning(color):
                    return math.inf, 1
                else:
                    return self.evaluate_game_state(child.data[1], child.data[0], color), 1
            # Play out the remainder of the game using a random policy
            while not child.is_terminal():
                child = random.choice(child.children)
            # Check if a winning state has been reached, and return math.inf if so
            if child.is_winning(color):
                return math.inf, 1
            # Update the wins and total counts
            total += 1
            if child.is_terminal():
                if child.is_winning(color):
                    return math.inf, total + 1
                else:
                    return self.evaluate_game_state(child.data[1], child.data[0], color), total + 1

        return self.evaluate_game_state(node.data[1], node.data[0], color), total

    def _traverse_tree(self, color, node):
        while node.children:
            non_fortify_children = [child for child in node.children if child[0].data["type"] != "f"]
            unexplored_children = [child for child in non_fortify_children if child[1].num_visits == 0]
            if len(unexplored_children) > 0:
                child_node = unexplored_children[0]
                child_node[1].num_visits += 1  # Increment num_visits for the child node
                return child_node[1], child_node[1].num_visits
            else:
                ucb_scores = [self._ucb(color, child, node, node.num_visits, child[1].num_visits) for child in
                              non_fortify_children]
                # print([edge.data["type"] for edge, _ in non_fortify_children],
                #       [edge.data["type"] for edge, _ in node.children])
                if len(ucb_scores) == 0 and len(node.children) == 1:
                    best_child = node.children[0]
                else:
                    best_child = non_fortify_children[np.argmax(ucb_scores)]

                node = best_child[1]
                node.num_visits += 1  # Increment num_visits for the selected node

        return node, node.num_visits

    def _sort_territory_neighbors(self, territory, gamestate):
        territory_neighbors = {}

        for t in self.territory_attack_map[territory]:
            territory_neighbors[t] = self._get_troop_count_from_territory(t, gamestate)

        return dict(sorted(territory_neighbors.items(), key=lambda entry: entry[1]))

    def _reinforce_weak_territories(self, color, troops, gamestate, territories_in_gs,
                                    weak_territory_count):
        color_idx = get_color_index(color)
        weak_territories = [t for t in gamestate if self._get_troop_count_from_territory(t, gamestate) < 2]
        weak_territories = sorted(weak_territories,
                                  key=lambda t: self._get_troop_count_from_territory(t, gamestate))
        weak_territories_dict = {t: self._get_troop_count_from_territory(t, gamestate) for t in weak_territories}
        allocated_troops = allocate_troops(troops, weak_territories_dict)

        for territory, troops_to_add in allocated_troops.items():
            gamestate[territory][color_idx].number += troops_to_add

        return gamestate, allocated_troops

    def _reinforce_owned_key_territories(self, color, troops, gamestate, territories_in_gs,
                                         key_territory_percentage,
                                         fallback_count):
        key_territories = get_key_territories()

        color_idx = get_color_index(color)
        owned_key_territories = [t for t in territories_in_gs[color] if t in key_territories]

        if len(owned_key_territories) == 0:
            return self._reinforce_weak_territories(color, troops, gamestate, territories_in_gs, fallback_count)


        weak_territories = [t for t in gamestate if self._get_troop_count_from_territory(t, gamestate) < 3 and t in
                            territories_in_gs[color]]
        weak_territories = sorted(weak_territories,
                                  key=lambda t: self._get_troop_count_from_territory(t, gamestate))
        weak_territories_dict = {t: self._get_troop_count_from_territory(t, gamestate) for t in weak_territories}

        troops_on_key_territories = math.floor(key_territory_percentage * troops)
        troops_on_weak_territories = troops - troops_on_key_territories

        key_territory_split = troops_on_key_territories // len(key_territories)

        for territory in owned_key_territories:
            gamestate[territory][color_idx].number += key_territory_split

        allocated_troops = allocate_troops(troops_on_weak_territories, weak_territories_dict)

        for territory, troops_to_add in allocated_troops.items():
            gamestate[territory][color_idx].number += troops_to_add

        return gamestate, allocated_troops

    def _reinforce_attacked_territories(self, color, troops, gamestate, territories_in_gs,
                                        attacked_territory_percentage, attack_count_in_gs,
                                        fallback_count):
        territories_owned_attack_counts = {t: attack_count_in_gs[t] for t in territories_in_gs[color] if
                                           attack_count_in_gs[t] > 0}

        color_idx = get_color_index(color)

        if len(territories_owned_attack_counts) == 0:
            return self._reinforce_weak_territories(color, troops, gamestate, territories_in_gs, fallback_count)

        allocated_troops = allocate_troops_by_attacks(territories_owned_attack_counts, troops)

        for territory, troops_to_add in allocated_troops.items():
            gamestate[territory][color_idx].number += troops_to_add

        return gamestate, allocated_troops

    # for attacking strategies, to keep the search tree limited, a maximum of 12 attacks are added
    def _aggressive_attack(self, selected_node, color, gamestate, territories_in_gs, attack_count_in_gs,
                           territories_owned_sorted_by_troops_max):

        # get the top 4 territories with the most troops on them as these are great for attacking
        for territory in territories_owned_sorted_by_troops_max[:5]:
            # get the top 3 territories with the least troops on them that are neighbors of one of
            # the top 4 territories
            sorted_attackable_territories = self._sort_territory_neighbors(territory, gamestate)
            attack_troops = self._get_troop_count_from_territory(territory, gamestate)

            i = 0
            for defence_territory in sorted_attackable_territories:
                if i == 4:
                    break
                defence_troops = self._get_troop_count_from_territory(defence_territory, gamestate)
                prob = calculate_attack_success_probability(attack_troops, defence_troops)

                # calculate how many attack and defence troops lost based on the probability of an
                # attack success

                new_gamestate = deepcopy(gamestate)
                new_territories_owned = deepcopy(territories_in_gs)
                new_attacks = deepcopy(attack_count_in_gs)

                attacking_count = self._get_troop_count_from_territory(territory, gamestate)
                defending_count = self._get_troop_count_from_territory(defence_territory, gamestate)
                win = False

                if prob > 0.5:
                    attacking_troops_lost = int(round(attacking_count * (1 - prob)))
                    defending_troops_lost = defending_count
                    win = True
                else:
                    attacking_troops_lost = attacking_count - 1
                    defending_troops_lost = int(round(defending_count * (1 - prob)))

                ocolor = find_owner_of_territory_in_gamestate(defence_territory, new_territories_owned)

                color_idx = get_color_index(color)
                ocolor_idx = get_color_index(ocolor)

                if win:
                    new_gamestate[territory][color_idx].number -= attacking_troops_lost + 1
                    new_gamestate[defence_territory][ocolor_idx].number = 1
                else:
                    new_gamestate[defence_territory][ocolor_idx].number -= defending_troops_lost
                    new_gamestate[territory][color_idx].number = 1

                if win:
                    new_territories_owned[color].append(defence_territory)
                    new_territories_owned[ocolor].remove(defence_territory)

                new_attacks[defence_territory] += 1

                selected_node.add_child(
                    TreeNode([new_territories_owned, new_gamestate, new_attacks]),
                    {"type": "a", "won": win, "attacking_territory":
                        territory, "defending_territory": defence_territory},
                )

                i += 1

        return selected_node

    def _guerilla_style_attack(self, color, selected_node, gamestate, territories_in_gs, attack_count_in_gs):
        territories_owned_by_others = [t for c, t in territories_in_gs.items() if color != c]
        territories_not_owned = []

        for a in territories_owned_by_others:
            for b in a:
                territories_not_owned.append(b)

        weakest_territories = {t: self._get_troop_count_from_territory(t, gamestate) for t in territories_not_owned}
        weakest_territories = dict(sorted(weakest_territories.items(), key=lambda entry: entry[1]))

        attackable_weak_territories = {}
        territories_owned = set(territories_in_gs[color])

        # add territory to attack with to dictionary
        for k in weakest_territories:
            neighbors_of_weak_territory = set(self.territory_attack_map[k])
            territory_to_attack_with = territories_owned.intersection(neighbors_of_weak_territory)

            if len(territory_to_attack_with) == 0:
                continue
            elif len(territory_to_attack_with) == 1:
                territory_to_attack_with = list(territory_to_attack_with)[0]
            else:
                # if there are more territories that can attack, choose the one with the highest # of troops
                index = np.argmax(
                    [self._get_troop_count_from_territory(t, gamestate) for t in territory_to_attack_with])
                territory_to_attack_with = list(territory_to_attack_with)[index]

            troops_on_weak_territory = self._get_troop_count_from_territory(k, gamestate)
            troops_on_territory_attacking = self._get_troop_count_from_territory(territory_to_attack_with, gamestate)

            # only attack weak territories if we can attack with more die
            if troops_on_territory_attacking - 1 <= troops_on_weak_territory:
                continue

            attackable_weak_territories[k] = territory_to_attack_with

        # as mentioned above attacks are limited to 12 for search tree performance
        i = 0
        for defence_territory, territory_to_attack_with in attackable_weak_territories.items():
            if i == 12:
                break

            new_gamestate = deepcopy(gamestate)
            new_territories_owned = deepcopy(territories_in_gs)
            new_attacks = deepcopy(attack_count_in_gs)

            win = False
            attack_troops = self._get_troop_count_from_territory(territory_to_attack_with, new_gamestate)
            defence_troops = self._get_troop_count_from_territory(defence_territory, new_gamestate)

            prob = calculate_attack_success_probability(attack_troops, defence_troops)

            if prob > 0.5:
                attacking_troops_lost = int(round(attack_troops * (1 - prob)))
                defending_troops_lost = defence_troops
                win = True
            else:
                attacking_troops_lost = attack_troops - 1
                defending_troops_lost = int(round(defence_troops * (1 - prob)))

            ocolor = find_owner_of_territory_in_gamestate(defence_territory, new_territories_owned)

            color_idx = get_color_index(color)
            ocolor_idx = get_color_index(ocolor)

            if win:
                new_gamestate[territory_to_attack_with][color_idx].number -= attacking_troops_lost + 1
                new_gamestate[defence_territory][ocolor_idx].number = 1
            else:
                new_gamestate[defence_territory][ocolor_idx].number -= defending_troops_lost
                new_gamestate[territory_to_attack_with][color_idx].number = 1

            if win:
                new_territories_owned[color].append(defence_territory)
                new_territories_owned[ocolor].remove(defence_territory)

            new_attacks[defence_territory] += 1

            selected_node.add_child(
                TreeNode([new_territories_owned, new_gamestate, new_attacks]),
                {"type": "a", "attacking_territory": territory_to_attack_with,
                 "won": win,
                 "defending_territory": defence_territory},
            )

            i += 1

        return selected_node

    def _blitz_attack(self, color, selected_node, gamestate, territories_in_gs, attack_count_in_gs):
        # this attacking strategy prioritizes attacking weak "key" territories to gain a strategic advantage
        key_territories = get_key_territories()

        sorted_key_territories = sorted(key_territories,
                                        key=lambda t: self._get_troop_count_from_territory(t, gamestate))
        attackable_key_territories = {}
        owned_territories = set(territories_in_gs[color])

        for territory in sorted_key_territories:
            if territory not in owned_territories:
                continue

            neighbors_of_territory = set(self.territory_attack_map[territory])

            territory_to_attack_with = neighbors_of_territory.intersection(owned_territories)

            if len(territory_to_attack_with) == 0:
                continue
            elif len(territory_to_attack_with) == 1:
                territory_to_attack_with = list(territory_to_attack_with)[0]
            else:
                index = np.argmax([t for t in territory_to_attack_with])
                territory_to_attack_with = list(territory_to_attack_with)[index]

            troops_on_weak_territory = self._get_troop_count_from_territory(territory, gamestate)
            troops_on_attacking_territory = self._get_troop_count_from_territory(territory_to_attack_with, gamestate)

            if troops_on_weak_territory == 0:
                continue

            if troops_on_attacking_territory == 1:
                continue

            if troops_on_attacking_territory - 1 <= troops_on_weak_territory:
                continue



            attackable_key_territories[territory] = territory_to_attack_with

        i = 0
        for defence_territory, territory_to_attack_with in attackable_key_territories.items():
            if i == 12:
                break

            new_gamestate = deepcopy(gamestate)
            new_territories_owned = deepcopy(territories_in_gs)
            new_attacks = deepcopy(attack_count_in_gs)

            win = False
            attack_troops = self._get_troop_count_from_territory(territory_to_attack_with, new_gamestate)
            defence_troops = self._get_troop_count_from_territory(defence_territory, new_gamestate)

            prob = calculate_attack_success_probability(attack_troops, defence_troops)

            if prob > 0.5:
                attacking_troops_lost = int(round(attack_troops * (1 - prob)))
                defending_troops_lost = defence_troops
                win = True
            else:
                attacking_troops_lost = attack_troops - 1
                defending_troops_lost = int(round(defence_troops * (1 - prob)))

            ocolor = find_owner_of_territory_in_gamestate(defence_territory, new_territories_owned)

            color_idx = get_color_index(color)
            ocolor_idx = get_color_index(ocolor)

            if win:
                new_gamestate[territory_to_attack_with][color_idx].number -= attacking_troops_lost + 1
                new_gamestate[defence_territory][ocolor_idx].number = 1
            else:
                new_gamestate[defence_territory][ocolor_idx].number -= defending_troops_lost
                new_gamestate[territory_to_attack_with][color_idx].number = 1

            #print(new_gamestate[territory_to_attack_with][color_idx].number, new_gamestate[defence_territory][ocolor_idx].number)

            if win:
                new_territories_owned[color].append(defence_territory)
                new_territories_owned[ocolor].remove(defence_territory)

            new_attacks[defence_territory] += 1

            selected_node.add_child(
                TreeNode([new_territories_owned, new_gamestate, new_attacks]),
                {"type": "a", "attacking_territory": territory_to_attack_with,
                 "won": win,
                 "defending_territory": defence_territory},
            )

            i += 1

        return selected_node

    def _transfer_troops(self, color, territory_attacking, territory_won, gamestate, territories_in_gs,
                         attack_count_in_gs,
                         re_attack_weight, isolation_weight,
                         key_territory_weight):
        all_neighbors = self.territory_attack_map[territory_won]
        owned_neighbors = [t for t in all_neighbors if t in territories_in_gs[color]]
        key_territories = get_key_territories()

        total_troops = self._get_troop_count_from_territory(territory_attacking, gamestate)

        isolation = len(owned_neighbors) / len(all_neighbors)

        troops_to_add = 0

        if territory_won in key_territories:
            troops_to_add += key_territory_weight * total_troops

        troops_to_add += attack_count_in_gs[territory_won] * re_attack_weight

        troops_to_add += isolation_weight * (total_troops * isolation)

        new_gamestate = deepcopy(gamestate)
        new_territories_owned = deepcopy(territories_in_gs)
        new_attacks = deepcopy(attack_count_in_gs)

        color_idx = get_color_index(color)

        if troops_to_add > total_troops:
            # if weights are not chosen correctly 1 troop will be added
            # this is to penalize incorrect selection of weights
            new_gamestate[territory_attacking][color_idx].number -= 1
            new_gamestate[territory_won][color_idx].number += 1
            return

        new_gamestate[territory_attacking][color_idx].number -= troops_to_add
        new_gamestate[territory_won][color_idx].number += troops_to_add

        return new_gamestate, new_territories_owned, new_attacks

    def _fortify_weakest_territories(self, color, gamestate, territories_in_gs):
        weakest_territories = {t: self._get_troop_count_from_territory(t, gamestate) for t in territories_in_gs[color]}
        sorted_weakest_territories = dict(sorted(weakest_territories.items(), key=lambda x: x[1]))

        get_allocation = lambda t: {x: self._get_troop_count_from_territory(x, gamestate) for x in
                                    self.territory_attack_map[t] if x in territories_in_gs[color]}
        get_total = lambda t: sum([self._get_troop_count_from_territory(x, gamestate) for x in
                                   self.territory_attack_map[t] if x in territories_in_gs[color]])

        sorted_weakest_territories_with_allocation_limit = {
            k: {"troops": v, "total_troops": get_total(k), "neighbors": get_allocation(k)} for k, v in
            sorted_weakest_territories.items()}

        target_territories = {}

        # cleanup array and add percentages
        for k, v in sorted_weakest_territories_with_allocation_limit.items():
            if len(v["neighbors"]) == 0:
                continue

            percentages = {}
            total_troops = v["total_troops"]
            value = v

            if total_troops == 0:
                continue

            for t, troops in v["neighbors"].items():
                percentages[t] = {"troops": troops, "percentage": troops / total_troops}

            value["neighbors"] = percentages
            target_territories[k] = value

        target_territories = dict(sorted(target_territories.items(), key=lambda x: x[1]["troops"]))

        new_gamestate = deepcopy(gamestate)
        new_territories = deepcopy(territories_in_gs)

        color_idx = get_color_index(color)
        full_map = sorted_weakest_territories_with_allocation_limit

        for weak_territory, information in target_territories.items():
            result = allocate_fortification_troops(full_map, target_territories, weak_territory,
                                                   information["total_troops"])

            for t, transfer in result.items():
                if transfer > 0:
                    if new_gamestate[t][color_idx].number - transfer < 0:
                        new_transfer = transfer - abs(new_gamestate[t][color_idx].number - transfer)
                        new_gamestate[t][color_idx].number -= new_transfer
                        new_gamestate[weak_territory][color_idx].number += new_transfer
                    else:
                        new_gamestate[weak_territory][color_idx].number += transfer
                        new_gamestate[t][color_idx].number -= transfer

        return new_gamestate, new_territories

    def find_best_move(self, color):
        print(color)
        moves = ["p", "a", "ap", "f"]
        search_tree = Tree([deepcopy(self.TERRITORIES_OWNED), deepcopy(self._troops_on_board),
                            deepcopy(self.TERRITORY_ATTACK_COUNT)])
        depth = 4
        selected_node = None

        i = 0
        while True:
            tree_depth = search_tree.get_num_layers()

            if tree_depth == depth:
                break

            # selection step
            if tree_depth == 1:
                selected_node = search_tree.get_root()
            else:
                selected_node, total_actions_taken = self._traverse_tree(color, search_tree.get_root())

            # expansion step
            possible_actions = moves
            edge_to_parent = None

            if selected_node.parent:
                edge_to_parent = selected_node.parent.get_edge_to_child(selected_node)

            previous_action_data = None if selected_node.parent is None else edge_to_parent.data
            previous_action = None if previous_action_data is None else previous_action_data["type"]

            # force fortification if depth about to be reached
            if tree_depth == depth - 1 and previous_action != "f":
                possible_actions = ["f"]

            if "p" in possible_actions and previous_action == "a":
                possible_actions.remove("p")
            elif previous_action == "f":
                possible_actions = []
            elif "ap" in possible_actions:
                possible_actions.remove("ap")

            # if action taken previously, then remove (except for attack)
            if previous_action != "a" and previous_action in possible_actions:
                possible_actions.remove(previous_action)

            gamestate = selected_node.data[1]
            territories_owned_in_gamestate = selected_node.data[0]
            attack_counts = selected_node.data[2]

            territories_owned_sorted_by_troops_max = sorted(territories_owned_in_gamestate[color], reverse=True,
                                                            key=lambda t:
                                                            self._get_troop_count_from_territory(t, gamestate))
            for action in possible_actions:
                if action == "a":
                    selected_node = self._blitz_attack(
                        color, selected_node, gamestate,
                        territories_owned_in_gamestate,
                        attack_counts,
                    )

                elif action == "p":
                    troops_by_territories = min(3, len(territories_owned_in_gamestate[color]) // 3)
                    troops_by_continent = self._get_continent_owned_bonus(color, territories_owned_in_gamestate)
                    troops_by_card = self._get_card_trade_bonus(color, territories_owned_in_gamestate)
                    total_troops = troops_by_territories + troops_by_continent + troops_by_card

                    new_gamestate = deepcopy(gamestate)
                    new_territories_owned = deepcopy(territories_owned_in_gamestate)
                    new_attacks = deepcopy(attack_counts)

                    # new_gamestate = \
                    #      self._reinforce_weak_territories(color, total_troops, new_gamestate,
                    #                                       territories_owned_in_gamestate, 3)
                    new_gamestate, allocated_troops = \
                        self._reinforce_owned_key_territories(color, total_troops, new_gamestate,
                                                              territories_owned_in_gamestate, 0.6, 3)
                    # new_gamestate = self._reinforce_attacked_territories(color, total_troops, new_gamestate,
                    #                                                      territories_owned_in_gamestate, 0.4, 3)

                    selected_node.add_child(
                        TreeNode([new_territories_owned, new_gamestate, new_attacks]),
                        {"type": "p", "territories_changed": {k: v for k, v in allocated_troops.items() if v > 0},
                         "troops": total_troops}
                    )

                elif action == "ap":
                    if not previous_action_data["won"]:
                        continue

                    attacking_territory = previous_action_data["attacking_territory"]
                    territory_won = previous_action_data["defending_territory"]

                    troops_on_attacking_territory = self._get_troop_count_from_territory(attacking_territory, gamestate)
                    troops_on_territory_won = self._get_troop_count_from_territory(territory_won, gamestate)

                    new_gamestate, new_territories_owned, new_attacks = \
                        self._transfer_troops(color, attacking_territory,
                                              territory_won,
                                              gamestate,
                                              territories_owned_in_gamestate,
                                              attack_counts, 0.1, 0.1,
                                              0.1)

                    selected_node.add_child(
                        TreeNode([new_territories_owned, new_gamestate, new_attacks]),
                        {"type": "ap"},
                    )

                else:
                    new_gamestate, new_territories = \
                        self._fortify_weakest_territories(color, gamestate,
                                                          territories_owned_in_gamestate)

                    new_attacks = deepcopy(attack_counts)

                    selected_node.add_child(
                        TreeNode([new_territories, new_gamestate, new_attacks]),
                        {"type": "f"},
                    )

            # simulation step
            if len(possible_actions) == 0:
                reward = self.evaluate_game_state(selected_node.data[1], selected_node.data[0], color)
                total = 0
            else:
                reward, total = self._simulate_game(color, selected_node)
            
            # backpropagate
            backpropagate(selected_node, reward, total)

            # if we choose to fortify, end turn now
            if edge_to_parent and edge_to_parent.data["type"] == "f":
                break

        root = search_tree.get_root()
        children = sorted([(node, node.num_visits) for _, node in root.children], reverse=True,
                          key=lambda item: item[1])
        best_child = children[0][0]


        edge = root.get_edge_to_child(best_child)
        color_idx = get_color_index(color)

        turn = [(edge, best_child)]

        # Take action
        while len(best_child.children) > 0:
            edge, best_child, _ = sorted([(e, node, node.num_visits) for e, node in best_child.children],
                                         reverse=True, key=lambda x: x[2])[0]
            turn.append((edge, best_child))

        final_position = turn[-1][1]
        self.TERRITORIES_OWNED, self._troops_on_board, self.TERRITORY_ATTACK_COUNT = final_position.data

        self._draw_card(color)
        self.change_turn()

    def run_place_troops(self):
        if not self.PICK_TERRITORIES_MODE:
            return

        self.ATTACK_MODE = False
        territories = list(self._location_troop_coordinates.keys())
        run = True

        while run:
            for index, color in enumerate(self.TERRITORIES_REMAINING_COUNT):
                if self.TERRITORIES_REMAINING_COUNT[color] == 0 and index == len(self.TERRITORIES_REMAINING_COUNT) - 1:
                    run = False
                elif self.TERRITORIES_REMAINING_COUNT[color] == 0:
                    continue

                territory_selected = ""
                if len(self.TERRITORIES_REMAINING) == 0:
                    territory_selected = random.choice(self.TERRITORIES_OWNED[color])
                else:
                    territory_selected = self._select_territory(color, self.TERRITORIES_REMAINING)
                    self.TERRITORIES_REMAINING.remove(territory_selected)
                    self.TERRITORIES_OWNED[color].append(territory_selected)

                color_index = get_color_index(color)

                self._troops_on_board[territory_selected][color_index].number += 1
                self.TERRITORIES_REMAINING_COUNT[color] -= 1

                self.change_turn()

        self.PICK_TERRITORIES_MODE = False
        self.ATTACK_MODE = True

    def _calculate_territories_owned_value(self, color):

        continents_information = {
            "AS": {"bonus": 7, "territory_count": 12},
            "AF": {"bonus": 3, "territory_count": 6},
            "NA": {"bonus": 5, "territory_count": 9},
            "SA": {"bonus": 2, "territory_count": 4},
            "AU": {"bonus": 2, "territory_count": 4},
            "EU": {"bonus": 5, "territory_count": 7}
        }

        territories_by_continent = {
            "NA": ["Alaska", "Northwest Territory", "Greenland", "Alberta", "Ontario", "Quebec",
                   "Western United States", "Eastern United States", "Central America"],
            "SA": ["Venezuela", "Peru", "Brazil", "Argentina"],
            "EU": ["Iceland", "Scandinavia", "Ukraine", "Great Britain", "Northern Europe", "Southern Europe",
                   "Western Europe"],
            "AF": ["North Africa", "Egypt", "East Africa", "Congo", "South Africa", "Madagascar"],
            "AS": ["Ural", "Siberia", "Yakutsk", "Kamchatka", "Afghanistan", "Middle East", "India", "China",
                   "Mongolia", "Japan", "Irkutsk", "Kazakhstan", "Siam"],
            "AU": ["Indonesia", "New Guinea", "Western Australia", "Eastern Australia"]
        }

        territories_owned = self.TERRITORIES_OWNED[color]

        value = 0

        for continent, information in continents_information.items():
            territories_in_continent = [t for t in territories_owned if t in territories_by_continent[continent]]

            continent_proportion = len(territories_in_continent) / information["territory_count"]
            continent_proportion_bonus = continent_proportion * information["bonus"]

            value += continent_proportion_bonus

        return value
        pass

    def _get_troop_count_from_territory(self, territory, gamestate):
        if gamestate is None:
            gamestate = self._troops_on_board
        for troop in gamestate[territory]:
            if troop.number > 0:
                return troop.number

        return 0

    def _get_troop_from_territory(self, territory, gamestate):
        if gamestate is None:
            gamestate = self._troops_on_board
        for troop in gamestate[territory]:
            if troop.number > 0:
                return troop

    def _calculate_troop_strength(self, color, gamestate):
        territories_owned = self.TERRITORIES_OWNED[color]
        colors = ["Red", "Black", "Light Blue", "Green"]
        colors.remove(color)

        total_troops = 0
        color_troops = 0

        for c in colors:
            for territory in self.TERRITORIES_OWNED[c]:
                troop_count = self._get_troop_count_from_territory(territory, gamestate)
                total_troops += 1

        for territory in self.TERRITORIES_OWNED[color]:
            troop_count = self._get_troop_count_from_territory(territory, gamestate)
            color_troops += 0 if troop_count is None else troop_count

        return round((color_troops / total_troops) * 100, 2)

    def _get_continents_owned(self, color, territories_in_gs):
        continent_bonus = self._get_continent_owned_bonus(color, territories_in_gs)

        return continent_bonus

    def evaluate_game_state(self, gamestate, territories_in_gs, color):
        num_territories_owned = len(territories_in_gs[color])
        territory_proportions = self._calculate_territories_owned_value(color)
        troop_strength = self._calculate_troop_strength(color, gamestate)
        continents_owned = self._get_continents_owned(color, territories_in_gs)
        # max_risk_on_position = random.randint(0, self.TURNS_PLAYED)

        geographic_positioning_coefficient = 0.75
        territories_owned_coefficient = 0.5
        troop_strength_coefficient = 0.4
        continents_owned_coefficient = 0.88
        # risk_coefficient = random.random() * max_risk_on_position

        return geographic_positioning_coefficient * territory_proportions + territories_owned_coefficient * \
               num_territories_owned + troop_strength * troop_strength_coefficient + continents_owned * \
               continents_owned_coefficient

    def run_attack_turns(self):
        if not self.ATTACK_MODE:
            return

        index = 0
        while True:
            if index == 50:
                break

            color = get_color_by_index(self.PLAYER)
            troops_by_territories = min(3, len(self.TERRITORIES_OWNED[color]) // 3)
            troops_by_continent = self._get_continent_owned_bonus(color)
            troops_by_card = self._get_card_trade_bonus(color)

            print(troops_by_card)

            total_troops_to_add = troops_by_territories + troops_by_continent + troops_by_card

            self._place_troops_before_attack(color, total_troops_to_add)
            self._attack(color)

            self._draw_card(color)
            self.change_turn()
            index += 1

        self.PICK_TERRITORIES_MODE = False

        self.ATTACK_MODE = False

    def draw(self):
        self.surface.blit(self.BACKGROUND, (0, 0))
        self.ui_callback()

        for _, troops in self._troops_on_board.items():
            for troop in troops:
                troop.draw()

        pygame.display.update()

    def _check_territory_owned(self, territory_to_attack):
        for color in self.TERRITORIES_OWNED.keys():
            color_index = get_color_index(color)
            if self._troops_on_board[territory_to_attack][color_index].number > 0:
                return True

        return False
