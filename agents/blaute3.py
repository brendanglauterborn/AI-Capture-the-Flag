import random
from collections import deque

class Agent:
    def __init__(self):
        #remember walls and open cells we’ve seen
        self.walls = set()
        self.free = set()
        self.edge = set()
        self.visited = set()
        self.last_opp_pos = None
        self.last_opp_step = None
        self.step = 0

    def get_action(self, state, agent_id):
        """Return one of: 'up', 'down', 'left', 'right', 'stay'"""

        self.step += 1

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

        rows, cols = grid_size

        #If flag is adjacent, grab it immediately
        for d, tile in info.items():
            if tile == "flag":
                return d

        #Aggressive logic: if opponent is adjacent, try to trap/herd them

        # directions where we see the opponent in adjacent cells
        adjacent_agent_dirs = [
            d for d, tile in info.items()
            if tile in ("agent1", "agent2")
        ]

        if adjacent_agent_dirs:
            # infer opponent position from our position + direction
            first_dir = adjacent_agent_dirs[0]
            dx_opp, dy_opp = dir_map[first_dir]
            opp = (me[0] + dx_opp, me[1] + dy_opp)
            ox, oy = opp

            # remember last known opponent position + step
            self.last_opp_pos = opp
            self.last_opp_step = self.step

            # count how many directions around the opponent are "blocked"
            # (off-grid, wall, or known edge)
            blocked = 0
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = ox + dx, oy + dy
                if not (0 <= nx < rows and 0 <= ny < cols):
                    blocked += 1
                    continue
                if (nx, ny) in self.walls or (nx, ny) in self.edge:
                    blocked += 1

            # side moves: moves we can take that keep us near but not on top of them
            side_moves = []
            for d, (dx, dy) in dir_map.items():
                nx, ny = me[0] + dx, me[1] + dy
                # don't walk into the opponent
                if (nx, ny) == opp:
                    continue
                # only consider safe tiles from our current perception
                if info.get(d) in ("empty", "flag"):
                    side_moves.append(d)

            r = random.random()

            # opponent is really cornered (3+ blocked directions):
            # mostly camp and let them run out of options
            # 80% stay, 20% move
            if blocked >= 3:
                if r < 0.8:     
                    return "stay"
                if side_moves:
                    return random.choice(side_moves)
                return "stay"

            # opponent somewhat boxed: mix camping + tightening the box
            # 20% stay, 80% move
            elif blocked == 2:
                if r < 0.2:     
                    return "stay"
                if side_moves:
                    return random.choice(side_moves)
                return "stay"

            # opponent has more room: herd more, camp less
            # 10% stay, 90% move
            else:
                if r < 0.1:     
                    return "stay"
                if side_moves:
                    return random.choice(side_moves)
                return "stay"

        # n-step chase toward last known opponent position
        chase_step = 7
        if self.last_opp_pos is not None and self.last_opp_step is not None:
            if self.step - self.last_opp_step <= chase_step:
                target = self.last_opp_pos
                if target != me:
                    tx, ty = target
                    dx = tx - me[0]
                    dy = ty - me[1]

                    chase_dirs = []
                    if dx < 0:
                        chase_dirs.append("up")
                    elif dx > 0:
                        chase_dirs.append("down")
                    if dy < 0:
                        chase_dirs.append("left")
                    elif dy > 0:
                        chase_dirs.append("right")

                    for cd in chase_dirs:
                        t = info.get(cd)
                        if t in ("empty", "flag"):
                            return cd

            if self.step - self.last_opp_step > chase_step:
                self.last_opp_pos = None
                self.last_opp_step = None

        #Normal exploration logic unvisited > visited, bfs to frontier when stuck

        safe_moves = []
        unvisited_moves = []

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
                continue

            # safe move
            self.free.add((nx, ny))
            safe_moves.append(d)

            # unvisited?
            if (nx, ny) not in self.visited:
                unvisited_moves.append(d)

        #Prefer unvisited safe moves first
        if unvisited_moves:
            return random.choice(unvisited_moves)

        # No unvisited neighbors so try to explore with BFS (frontier-based)
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
