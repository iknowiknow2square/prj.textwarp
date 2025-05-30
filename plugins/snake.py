import random
import hashlib
from plugins.base import Plugin
import curses

class Snake:
    """A snake that moves around the game world."""
    
    def __init__(self, game, x, y):
        self.x = x
        self.y = y
        self.length = 3
        self.max_length = 15  # Maximum length a snake can grow to
        self.body = [(x, y)]
        self.game = game
        self.direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
        self.time_to_move = 0
        self.move_interval = 0.5  # seconds between moves
        self.rattles = 0  # Number of rattles (red dots) at the end of the snake
        
    def update(self, dt):
        """Update the snake's position."""
        self.time_to_move -= dt
        if self.time_to_move <= 0:
            self.time_to_move = self.move_interval
            
            # Randomly change direction sometimes
            if random.random() < 0.3:
                self.direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
                
            # Move the snake
            head_x, head_y = self.body[0]
            dx, dy = self.direction
            new_head = (head_x + dx, head_y + dy)
            
            # Check if there's an egg at the new position
            world_x = new_head[0] + self.game.world_x
            world_y = new_head[1] + self.game.world_y
            
            # Convert world coordinates to integers before calculating location_id
            int_world_x = int(round(world_x))
            int_world_y = int(round(world_y))
            
            location_id = (int_world_x + int_world_y * 1000) % 127
            if chr(location_id) == '0':  # Found an egg
                # Only grow if we haven't reached max length
                if self.length < self.max_length:
                    self.length += 1
                # Create a space where the egg was
                space_key = hashlib.md5(f"{int_world_x},{int_world_y}".encode()).hexdigest()
                self.game.spaces[space_key] = (int_world_x, int_world_y)
                self.game.save_spaces()
                
            # Add the new head
            self.body.insert(0, new_head)
            
            # Remove the tail if we're longer than our length plus rattles
            while len(self.body) > self.length + self.rattles:
                self.body.pop()
                
    def render(self, screen):
        """Render the snake on the screen."""
        for i, (x, y) in enumerate(self.body):
            # Only render if the body segment is on screen
            screen_x = x + self.game.max_x // 2
            screen_y = y + self.game.max_y // 2
            
            if 0 <= screen_x < self.game.max_x and 0 <= screen_y < self.game.max_y:
                # Determine character and color based on position
                if i == 0:
                    # Head
                    char = 'S'
                    color = self.game.snake_color
                elif i >= self.length:
                    # Rattle (red dot)
                    char = '.'
                    color = curses.color_pair(1)  # Red color
                else:
                    # Body
                    char = 's'
                    color = self.game.snake_color
                
                # Add a visual indicator when snake is at max length
                attr = curses.A_BOLD if self.length >= self.max_length else 0
                
                try:
                    # Use the appropriate color
                    screen.addstr(screen_y, screen_x, char, color | attr)
                except:
                    # Ignore errors from writing to the bottom-right corner
                    pass
                    
    def bite(self, other_snake):
        """Bite another snake, gaining rattles and causing the other snake to lose a segment."""
        # Add two rattles to this snake
        self.rattles += 2
        
        # Remove a middle segment from the other snake if possible
        if len(other_snake.body) > 3:  # Only remove if the snake has more than head + 2 body segments
            middle_index = len(other_snake.body) // 2
            other_snake.body.pop(middle_index)
            other_snake.length -= 1
            
            # Show a message
            self.game.message = f"Snake bite! One snake lost a segment, another gained rattles."
            self.game.message_timeout = 2.0
            
            return True
        return False

class SnakePlugin(Plugin):
    """A plugin that adds snakes to the game world."""
    
    def __init__(self, game):
        super().__init__(game)
        self.snakes = []
        self.spawn_timer = 0
        self.spawn_interval = 10  # seconds between snake spawns
        self.max_snakes = 5
        
    def update(self, dt):
        """Update all snakes and potentially spawn new ones."""
        if not self.active:
            return
            
        # Update existing snakes
        for snake in self.snakes:
            snake.update(dt)
            
        # Check for snake collisions
        self.check_snake_collisions()
            
        # Maybe spawn a new snake
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            self.try_spawn_snake()
            
    def render(self, screen):
        """Render all snakes."""
        if not self.active:
            return
            
        for snake in self.snakes:
            snake.render(screen)
            
    def check_snake_collisions(self):
        """Check if any snake's head is colliding with another snake's body."""
        for i, snake1 in enumerate(self.snakes):
            if len(snake1.body) == 0:
                continue
                
            head1 = snake1.body[0]
            
            for j, snake2 in enumerate(self.snakes):
                if i == j or len(snake2.body) < 2:
                    continue
                    
                # Check if snake1's head is on any of snake2's body segments (excluding head)
                for k, segment in enumerate(snake2.body[1:], 1):
                    if head1 == segment:
                        # Snake1 bites snake2
                        snake1.bite(snake2)
                        break
            
    def try_spawn_snake(self):
        """Try to spawn a new snake at a random location."""
        if len(self.snakes) >= self.max_snakes:
            return False
            
        # Try to find a good spawn location
        for _ in range(10):  # Try 10 times
            # Choose a random location near the player
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)
            world_x = self.game.world_x + offset_x
            world_y = self.game.world_y + offset_y
            
            # Check if the location is suitable (near a plant)
            # Convert world coordinates to integers before calculating location_id
            int_world_x = int(round(world_x))
            int_world_y = int(round(world_y))
            
            location_id = (int_world_x + int_world_y * 1000) % 127
            if chr(location_id) == '@':
                # Create a new snake
                snake = Snake(self.game, offset_x, offset_y)
                self.snakes.append(snake)
                return True
                
        return False
