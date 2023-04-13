class Edge:
    def __init__(self, parent_node, child_node, data=None):
        self.parent = parent_node
        self.child = child_node
        self.data = data


class TreeNode:
    def __init__(self, data):
        self.data = data
        self.children = []
        self.parent = None
        self.num_visits = 0
        self.reward = 0

    def __str__(self):
        return f"Num Visits: {self.num_visits} Data: {self.data}"

    def add_child(self, child_node, data=None):
        # if self._is_descendant(child_node):
        #     return  # Avoid adding a cycle to the tree
        edge = Edge(self, child_node, data)
        child_node.parent = self
        self.children.append((edge, child_node))

    def _is_descendant(self, node):
        """Check if node is a descendant of self."""
        stack = [self]
        while stack:
            curr_node = stack.pop()
            if curr_node == node:
                return True
            for edge in curr_node.children:
                if edge.child not in stack:
                    stack.append(edge.child)
        return False

    def get_edge_to_child(self, child_node):
        for edge, child in self.children:
            if edge.child == child_node:
                return edge
        return None

    def is_terminal(self, color):
        all_territories = []
        for v in self.data[0].values():
            for i in v:
                all_territories.append(i)


        wins = [len(self.data[0][color]) == len(all_territories) for color in self.data[0]]

        return True in wins

    def is_winning(self, color):
        all_territories = []
        for v in self.data[0].values():
            for i in v:
                all_territories.append(i)

        return len(self.data[0][color]) == len(all_territories)


def get_troop_count_from_territory_ext(territory, gamestate):
    for troop in gamestate[territory]:
        if troop.number > 0:
            return troop.number

    return 0


def _pretty_print_data(node):
    string = ""
    for k in node:
        troop_count = get_troop_count_from_territory_ext(k, node)
        string += str(troop_count)

    return string


class Tree:
    def __init__(self, root_node):
        self.root = TreeNode(root_node)

    def get_root(self):
        return self.root

    def __str__(self):
        return self._print_tree(self.root)

    def _print_tree(self, node, level=0, visited=None):
        if visited is None:
            visited = set()

        node_data = None
        edge = None

        if node != self.root:
            edge, node = node

        visited.add(node)
        node_data = node.data[1]  # unpack tuple and then get gamestate

        action = None
        if edge:
            if type(edge.data) == type(dict()):
                action = edge.data["type"]
            else:
                action = edge.data

        result = "\t" * level + f"{node.num_visits} {action} {_pretty_print_data(node_data)}\n"
        for child in node.children:
            child_data = child
            if child not in visited:
                result += "\t" * level + "|\n"
                result += self._print_tree(child, level + 1, visited)
            else:
                cycle_index = node.children.index(child)
                cycle_path = node.children[cycle_index:]
                result += "\t" * level + "|\n"
                result += "\t" * (
                            level + 1) + f"{_pretty_print_data(child_data)} (cycle: {' -> '.join(map(str, cycle_path))})\n"

        visited.remove(node)
        return result

    def get_num_layers(self, node=None):
        """
        Returns the number of layers in the tree, including the root.
        """
        if node is None:
            node = self.root
        if not node.children:
            return 1
        else:
            max_depth = 0
            for child in node.children:
                child_depth = self.get_num_layers(child[1])
                if child_depth > max_depth:
                    max_depth = child_depth
            return max_depth + 1

