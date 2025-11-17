import random
from collections import deque

class Agent:
    def __init__(self):
        #remember walls and open cells we’ve seen
        self.walls = set()
        self.free = set()
        self.edge = set()
        self.visited = set()

    def get_action(self, state, agent_id):
        """Return one of: 'up', 'down', 'left', 'right', 'stay'"""

        #get my position
        me = tuple(state["agent1_pos"] if agent_id == 1 else state["agent2_pos"])
        #get grid size
        grid_size = tuple(state.get("gridsize", (10,10)))

        #get adjacent info 
        adj = state.get("adjacent_info", {}) or {}
        info = {}
        for d in ("up", "down", "left", "right"):
            info[d] = adj.get(d)

        # mark current cell free + visited
        self.free.add(me)
        self.visited.add(me)

        dir_map = {
            "up":    (-1, 0),
            "down":  (1, 0),
            "left":  (0, -1),
            "right": (0, 1)
        }

        safe_moves = []
        unvisited_moves = []

        # who is the opponent label in the local view
        opp_label = "agent2" if agent_id == 1 else "agent1"

        for d, tile in info.items():
            dx, dy = dir_map[d]
            nx, ny = me[0] + dx, me[1] + dy

            # wall / edge
            if tile == "wall":
                self.walls.add((nx, ny))
                continue
            if tile is None:
                self.edge.add((nx, ny))
                continue

            # agent blocking
            if tile in ("agent1", "agent2"):
                # don't walk into the other agent
                continue

            # safe move
            self.free.add((nx, ny))
            safe_moves.append(d)

            # unvisited?
            if (nx, ny) not in self.visited:
                unvisited_moves.append(d)

            # flag found
            if tile == "flag":
                return d

        # simple blocking logic
        # if the opponent is adjacent and we have no unvisited neighbors,
        # stay put to act as a wall and maybe farm +5 / +100
        opponent_adjacent = any(tile == opp_label for tile in info.values())
        if opponent_adjacent and not unvisited_moves:
            return "stay"
    

        # Prefer unvisited safe moves first
        if unvisited_moves:
            return random.choice(unvisited_moves)

        # No unvisited neighbors → try to explore with BFS (frontier-based)
        frontier = self.get_frontier(grid_size)
        targets = [f for f in frontier if f != me]

        if targets:
            path = self.bfs(me, targets, grid_size)
            if path and len(path) >= 2:
                nx, ny = path[1]
                dx = nx - me[0]
                dy = ny - me[1]

                if dx == -1: return "up"
                if dx == 1:  return "down"
                if dy == -1: return "left"
                if dy == 1:  return "right"

        # If BFS failed or no frontier, fall back to any safe adjacent move
        if safe_moves:
            return random.choice(safe_moves)

        # If totally stuck, stay
        return "stay"

    def get_frontier(self, grid_size):
        rows, cols = grid_size
        frontier = []

        for x, y in self.free:
            # Check neighbors for unknowns
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if not (0 <= nx < rows and 0 <= ny < cols): 
                    continue

                # A frontier tile borders unexplored space
                if (nx,ny) not in self.free and (nx,ny) not in self.walls:
                    frontier.append((x,y))
                    break

        return frontier

    def bfs(self, start, targets, grid_size):
        rows, cols = grid_size
        queue = deque([start])
        parent = {start: None}
        targets = set(targets)

        while queue:
            cur = queue.popleft()
            if cur in targets:
                # reconstruct path
                path = []
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                return path[::-1]

            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = cur[0]+dx, cur[1]+dy
                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                nxt = (nx, ny)

                if nxt in self.walls:
                    continue
                if nxt not in self.free:
                    continue
                if nxt not in parent:
                    parent[nxt] = cur
                    queue.append(nxt)

        return None
