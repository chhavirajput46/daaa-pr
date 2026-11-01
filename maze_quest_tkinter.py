import tkinter as tk
from tkinter import ttk, messagebox
import random
import time
import math
import threading
import sys

# Maze Quest - Python Tkinter DAA Mini Project
# Algorithms: Randomized DFS maze generation and BFS shortest-path search.
# Sound is generated using the operating system's built-in beep where available.
# No external packages or sound files are required.

try:
    import winsound  # Available on Windows
except ImportError:
    winsound = None


class MazeQuest:
    def __init__(self, root):
        self.root = root
        self.root.title("Maze Quest - DAA Mini Project")
        self.root.configure(bg="#101827")
        self.root.resizable(False, False)

        self.cell = 24
        self.rows = 19
        self.cols = 25
        self.maze = []
        self.player_positions = [(1, 1), (1, 1)]
        self.player_steps = [0, 0]
        self.players_enabled = True
        self.game_over = False
        self.sound_enabled = True
        self.music_enabled = False
        self.music_thread_running = False
        self.music_stop = threading.Event()
        self.generation_ms = 0.0
        self.pathfinding_ms = 0.0
        self.shortest_path = []
        self.show_hint = False
        self.animating = False
        self.goal_pulse = 0
        self.particles = []
        self.particle_animation_scheduled = False
        self.winner = None

        self._build_ui()
        self.new_game()
        self._pulse_goal()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#101827")
        header.pack(fill="x", padx=14, pady=(12, 4))

        tk.Label(
            header, text="🧩 MAZE QUEST",
            font=("Segoe UI", 22, "bold"),
            fg="#f8fafc", bg="#101827"
        ).pack(side="left")

        tk.Label(
            header, text="DFS GENERATION  •  BFS PATHFINDING",
            font=("Segoe UI", 9, "bold"),
            fg="#93c5fd", bg="#101827"
        ).pack(side="right", pady=8)

        controls = tk.Frame(self.root, bg="#182338", padx=10, pady=8)
        controls.pack(fill="x", padx=14, pady=6)

        tk.Label(controls, text="Maze size:", bg="#182338", fg="white",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(0, 5))

        self.difficulty = tk.StringVar(value="Medium")
        self.size_box = ttk.Combobox(
            controls, textvariable=self.difficulty,
            values=("Small", "Medium", "Large"), state="readonly", width=9
        )
        self.size_box.grid(row=0, column=1, padx=4)

        self.mode_var = tk.StringVar(value="2 Players")
        tk.Label(controls, text="Mode:", bg="#182338", fg="white",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=(12, 5))
        self.mode_box = ttk.Combobox(
            controls, textvariable=self.mode_var,
            values=("1 Player", "2 Players"), state="readonly", width=10
        )
        self.mode_box.grid(row=0, column=3, padx=4)

        tk.Button(
            controls, text="New Maze", command=self.new_game,
            bg="#2563eb", fg="white", activebackground="#1d4ed8",
            activeforeground="white", relief="flat", padx=10, pady=5,
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=4, padx=(12, 4))

        tk.Button(
            controls, text="Show / Hide Hint", command=self.toggle_hint,
            bg="#475569", fg="white", relief="flat", padx=8, pady=5,
            font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=5, padx=4)

        self.sound_button = tk.Button(
            controls, text="Sound: ON", command=self.toggle_sound,
            bg="#0f766e", fg="white", relief="flat", padx=8, pady=5,
            font=("Segoe UI", 9, "bold")
        )
        self.sound_button.grid(row=0, column=6, padx=4)

        self.music_button = tk.Button(
            controls, text="Music: OFF", command=self.toggle_music,
            bg="#7c3aed", fg="white", relief="flat", padx=8, pady=5,
            font=("Segoe UI", 9, "bold")
        )
        self.music_button.grid(row=0, column=7, padx=4)

        self.canvas = tk.Canvas(
            self.root, width=self.cols * self.cell, height=self.rows * self.cell,
            bg="#0b1220", highlightthickness=2, highlightbackground="#334155"
        )
        self.canvas.pack(padx=14, pady=8)

        footer = tk.Frame(self.root, bg="#101827")
        footer.pack(fill="x", padx=14, pady=(0, 12))

        self.status_label = tk.Label(
            footer, text="Use WASD for Player 1 and arrow keys for Player 2.",
            bg="#101827", fg="#e2e8f0", font=("Segoe UI", 10)
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        stats = tk.Frame(footer, bg="#101827")
        stats.pack(fill="x")
        self.stats_label = tk.Label(
            stats, text="", bg="#101827", fg="#93c5fd",
            font=("Consolas", 9), justify="left"
        )
        self.stats_label.pack(side="left", anchor="w")

        legend = tk.Label(
            stats,
            text="P1 ●  P2 ●  GOAL ★",
            bg="#101827", fg="#cbd5e1", font=("Segoe UI", 9, "bold")
        )
        legend.pack(side="right", anchor="e")

        self.root.bind("<KeyPress>", self._on_key)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

    def _dimensions(self):
        size = self.difficulty.get()
        if size == "Small":
            return 13, 17
        if size == "Large":
            return 25, 33
        return 19, 25

    def _generate_maze(self, rows, cols):
        # Start with all walls. DFS carves corridors two cells at a time.
        maze = [[1 for _ in range(cols)] for _ in range(rows)]
        start = (1, 1)
        maze[1][1] = 0
        stack = [start]
        directions = [(0, 2), (0, -2), (2, 0), (-2, 0)]

        while stack:
            r, c = stack[-1]
            candidates = []
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 1 <= nr < rows - 1 and 1 <= nc < cols - 1 and maze[nr][nc] == 1:
                    candidates.append((nr, nc, dr, dc))

            if candidates:
                nr, nc, dr, dc = random.choice(candidates)
                maze[r + dr // 2][c + dc // 2] = 0
                maze[nr][nc] = 0
                stack.append((nr, nc))
            else:
                stack.pop()

        # Ensure goal is a corridor and connected to the generated maze.
        goal = (rows - 2, cols - 2)
        maze[goal[0]][goal[1]] = 0
        # Carving the last row/column connection guarantees reachability.
        r, c = goal
        while c > 1 and maze[r][c - 1] == 1:
            c -= 1
            maze[r][c] = 0
        while r > 1 and maze[r - 1][c] == 1:
            r -= 1
            maze[r][c] = 0
        return maze

    def _bfs(self, start, goal):
        # BFS on an unweighted grid finds a shortest path.
        from collections import deque
        queue = deque([start])
        previous = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            r, c = current
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (r + dr, c + dc)
                nr, nc = nxt
                if (0 <= nr < self.rows and 0 <= nc < self.cols
                        and self.maze[nr][nc] == 0 and nxt not in previous):
                    previous[nxt] = current
                    queue.append(nxt)
        if goal not in previous:
            return []
        path = []
        current = goal
        while current is not None:
            path.append(current)
            current = previous[current]
        return list(reversed(path))

    def new_game(self):
        self.rows, self.cols = self._dimensions()
        self.canvas.config(width=self.cols * self.cell, height=self.rows * self.cell)
        started = time.perf_counter()
        self.maze = self._generate_maze(self.rows, self.cols)
        self.generation_ms = (time.perf_counter() - started) * 1000

        self.start = (1, 1)
        self.goal = (self.rows - 2, self.cols - 2)
        self.player_positions = [self.start, self.start]
        self.player_steps = [0, 0]
        self.players_enabled = self.mode_var.get() == "2 Players"
        self.game_over = False
        self.winner = None
        self.show_hint = False
        self.particles = []

        started = time.perf_counter()
        self.shortest_path = self._bfs(self.start, self.goal)
        self.pathfinding_ms = (time.perf_counter() - started) * 1000

        self.status_label.config(
            text="Player 1: W A S D    |    Player 2: Arrow keys    |    Reach ★ to win!"
        )
        self._draw()
        self._update_stats()
        self._tone("new")
        if self.music_enabled:
            self._start_music()

    def toggle_hint(self):
        self.show_hint = not self.show_hint
        self._draw()

    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.sound_button.config(
            text=f"Sound: {'ON' if self.sound_enabled else 'OFF'}",
            bg="#0f766e" if self.sound_enabled else "#475569"
        )
        if not self.sound_enabled:
            self._stop_music()
            self.music_enabled = False
            self.music_button.config(text="Music: OFF", bg="#475569")
        elif self.music_enabled:
            self._start_music()

    def toggle_music(self):
        if not winsound:
            messagebox.showinfo(
                "Music availability",
                "Looping synthesized music currently uses Windows winsound. "
                "On this computer, movement and visual gameplay still work; "
                "use Windows to enable the built-in melody."
            )
            return
        self.music_enabled = not self.music_enabled
        self.music_button.config(
            text=f"Music: {'ON' if self.music_enabled else 'OFF'}",
            bg="#7c3aed" if self.music_enabled else "#475569"
        )
        if self.music_enabled and self.sound_enabled:
            self._start_music()
        else:
            self._stop_music()

    def _tone(self, kind):
        if not self.sound_enabled:
            return
        # Beeps are asynchronous on Windows; other platforms simply skip audio.
        if winsound:
            tones = {
                "move": (660, 35),
                "new": (520, 80),
                "win": (880, 140),
                "goal": (1040, 100),
                "bump": (220, 45),
            }
            freq, duration = tones.get(kind, (500, 50))
            try:
                winsound.Beep(freq, duration)
            except RuntimeError:
                pass
        else:
            # A visible fallback indicator for platforms without winsound.
            if kind == "win":
                self.root.bell()

    def _start_music(self):
        # Lightweight looping melody. Windows only; uses built-in system beeps.
        if not winsound or self.music_thread_running or not self.sound_enabled:
            return
        self.music_stop.clear()
        self.music_thread_running = True

        def play():
            melody = [(392, 120), (494, 120), (587, 180), (494, 120),
                      (440, 120), (523, 180), (392, 220)]
            while not self.music_stop.is_set() and self.sound_enabled:
                for freq, duration in melody:
                    if self.music_stop.is_set() or not self.sound_enabled:
                        break
                    try:
                        winsound.Beep(freq, duration)
                    except RuntimeError:
                        break
                    self.music_stop.wait(0.04)
            self.music_thread_running = False

        threading.Thread(target=play, daemon=True).start()

    def _stop_music(self):
        self.music_stop.set()
        self.music_enabled = False

    def _on_key(self, event):
        if self.game_over:
            return

        key = event.keysym.lower()
        moves = {
            "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0),
            "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)
        }

        player_index = 0 if key in ("w", "a", "s", "d") else 1
        if key not in moves:
            return
        if player_index == 1 and not self.players_enabled:
            return

        dx, dy = moves[key]
        row, col = self.player_positions[player_index]
        new_row, new_col = row + dy, col + dx

        if (0 <= new_row < self.rows and 0 <= new_col < self.cols
                and self.maze[new_row][new_col] == 0):
            self.player_positions[player_index] = (new_row, new_col)
            self.player_steps[player_index] += 1
            self._tone("move")
            self._add_particles(new_row, new_col, player_index)
            if (new_row, new_col) == self.goal:
                self._win(player_index)
            self._draw()
            self._update_stats()
        else:
            self._tone("bump")

    def _win(self, player_index):
        self.game_over = True
        self.winner = player_index
        self._tone("win")
        name = "Player 1" if player_index == 0 else "Player 2"
        self.status_label.config(text=f"🏆 {name} wins! Click New Maze to play again.")
        self._celebrate(0)

    def _add_particles(self, row, col, player_index):
        x = col * self.cell + self.cell / 2
        y = row * self.cell + self.cell / 2
        color = "#38bdf8" if player_index == 0 else "#fb7185"
        for _ in range(5):
            angle = random.random() * math.tau
            speed = random.uniform(1, 3)
            self.particles.append({
                "x": x, "y": y,
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed,
                "life": 7, "color": color
            })

    def _celebrate(self, frame):
        if frame >= 12:
            return
        self._draw()
        for _ in range(8):
            x = random.randint(10, self.cols * self.cell - 10)
            y = random.randint(10, self.rows * self.cell - 10)
            color = random.choice(["#facc15", "#34d399", "#f472b6", "#60a5fa"])
            self.canvas.create_oval(x, y, x + 6, y + 6, fill=color, outline="")
        self.root.after(100, lambda: self._celebrate(frame + 1))

    def _pulse_goal(self):
        self.goal_pulse = (self.goal_pulse + 1) % 12
        if self.maze:
            self._draw()
        self.root.after(180, self._pulse_goal)

    def _draw(self):
        self.canvas.delete("all")
        if not self.maze:
            return

        # Optional shortest-path hint.
        if self.show_hint:
            for r, c in self.shortest_path:
                x1, y1 = c * self.cell + 7, r * self.cell + 7
                x2, y2 = x1 + self.cell - 14, y1 + self.cell - 14
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill="#334155", outline=""
                )

        # Draw walls and passages.
        for r in range(self.rows):
            for c in range(self.cols):
                x1, y1 = c * self.cell, r * self.cell
                x2, y2 = x1 + self.cell, y1 + self.cell
                if self.maze[r][c] == 1:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#263449", outline="#263449"
                    )
                else:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill="#111c2e", outline="#111c2e"
                    )

        # Animated goal glow.
        gr, gc = self.goal
        gx, gy = gc * self.cell + self.cell / 2, gr * self.cell + self.cell / 2
        radius = 7 + (self.goal_pulse % 4)
        self.canvas.create_oval(
            gx - radius, gy - radius, gx + radius, gy + radius,
            fill="#facc15", outline="#fef08a", width=2
        )
        self.canvas.create_text(
            gx, gy, text="★", fill="#713f12",
            font=("Segoe UI", 11, "bold")
        )

        # Starting point marker.
        sr, sc = self.start
        self.canvas.create_oval(
            sc * self.cell + 6, sr * self.cell + 6,
            sc * self.cell + self.cell - 6, sr * self.cell + self.cell - 6,
            fill="#64748b", outline=""
        )

        # Particle trails.
        live_particles = []
        for p in self.particles:
            if p["life"] > 0:
                p["x"] += p["dx"]
                p["y"] += p["dy"]
                p["life"] -= 1
                live_particles.append(p)
                self.canvas.create_oval(
                    p["x"] - 2, p["y"] - 2, p["x"] + 2, p["y"] + 2,
                    fill=p["color"], outline=""
                )
        self.particles = live_particles
        if self.particles and not self.particle_animation_scheduled:
            self.particle_animation_scheduled = True
            self.root.after(30, self._draw_particles_only)

        # Players.
        colors = ["#38bdf8", "#fb7185"]
        labels = ["1", "2"]
        for i, (pr, pc) in enumerate(self.player_positions):
            if i == 1 and not self.players_enabled:
                continue
            cx = pc * self.cell + self.cell / 2
            cy = pr * self.cell + self.cell / 2
            self.canvas.create_oval(
                cx - 8, cy - 8, cx + 8, cy + 8,
                fill=colors[i], outline="white", width=2
            )
            self.canvas.create_text(
                cx, cy, text=labels[i], fill="#0b1220",
                font=("Segoe UI", 8, "bold")
            )

        if self.game_over:
            self.canvas.create_rectangle(
                8, 8, self.cols * self.cell - 8, 38,
                fill="#064e3b", outline="#34d399", width=2
            )
            name = "PLAYER 1 WINS!" if self.winner == 0 else "PLAYER 2 WINS!"
            self.canvas.create_text(
                self.cols * self.cell / 2, 23, text=name,
                fill="#ecfdf5", font=("Segoe UI", 13, "bold")
            )

    def _draw_particles_only(self):
        # Schedule only one animation callback at a time.
        self.particle_animation_scheduled = False
        if self.particles:
            self._draw()

    def _update_stats(self):
        p1 = self.player_steps[0]
        p2 = self.player_steps[1] if self.players_enabled else 0
        shortest = max(0, len(self.shortest_path) - 1)
        self.stats_label.config(
            text=f"Generation: {self.generation_ms:.3f} ms    "
                 f"BFS: {self.pathfinding_ms:.3f} ms    "
                 f"Shortest path: {shortest} steps\n"
                 f"Player 1 steps: {p1}    Player 2 steps: {p2}    "
                 f"Maze cells: {self.rows * self.cols}"
        )


def main():
    root = tk.Tk()
    app = MazeQuest(root)
    root.mainloop()


if __name__ == "__main__":
    main()
