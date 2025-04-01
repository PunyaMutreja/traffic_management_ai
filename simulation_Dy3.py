import pygame
import random
import numpy as np
from collections import defaultdict
from sklearn.neighbors import KNeighborsClassifier

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Smart Traffic Light Control - Density Based")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
BLUE = (0, 0, 255)
LIGHT_BLUE = (100, 100, 255)

# Directions
NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

# Vehicle states
APPROACHING = 0
IN_INTERSECTION = 1
CLEARED = 2

# Intersection boundaries
INTERSECTION_TOP = 200
INTERSECTION_BOTTOM = 400
INTERSECTION_LEFT = 250
INTERSECTION_RIGHT = 550

class Vehicle:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = random.uniform(2.0, 3.5)
        self.state = APPROACHING
        self.width = 30 if direction in [NORTH, SOUTH] else 50
        self.height = 50 if direction in [NORTH, SOUTH] else 30
        
        # Adjust starting position based on direction
        if direction == NORTH:
            self.y = HEIGHT + 50
            self.x = random.randint(INTERSECTION_LEFT + 50, INTERSECTION_RIGHT - 50)
        elif direction == SOUTH:
            self.y = -50
            self.x = random.randint(INTERSECTION_LEFT + 50, INTERSECTION_RIGHT - 50)
        elif direction == EAST:
            self.x = -50
            self.y = random.randint(INTERSECTION_TOP + 50, INTERSECTION_BOTTOM - 50)
        elif direction == WEST:
            self.x = WIDTH + 50
            self.y = random.randint(INTERSECTION_TOP + 50, INTERSECTION_BOTTOM - 50)

    def update_state(self):
        if self.direction == NORTH:
            if INTERSECTION_TOP < self.y <= INTERSECTION_BOTTOM:
                self.state = IN_INTERSECTION
            elif self.y <= INTERSECTION_TOP:
                self.state = CLEARED
        elif self.direction == SOUTH:
            if INTERSECTION_TOP <= self.y < INTERSECTION_BOTTOM:
                self.state = IN_INTERSECTION
            elif self.y >= INTERSECTION_BOTTOM:
                self.state = CLEARED
        elif self.direction == EAST:
            if INTERSECTION_LEFT <= self.x < INTERSECTION_RIGHT:
                self.state = IN_INTERSECTION
            elif self.x >= INTERSECTION_RIGHT:
                self.state = CLEARED
        elif self.direction == WEST:
            if INTERSECTION_LEFT < self.x <= INTERSECTION_RIGHT:
                self.state = IN_INTERSECTION
            elif self.x <= INTERSECTION_LEFT:
                self.state = CLEARED

    def move(self, light_state, yellow_light):
        # Only stop if approaching a red or yellow light
        if self.state == APPROACHING:
            if light_state[self.direction] == RED or (
                yellow_light[self.direction] and not self.state == IN_INTERSECTION):
                return  # Don't move if should stop
        
        # Move based on direction
        if self.direction == NORTH:
            self.y -= self.speed
        elif self.direction == SOUTH:
            self.y += self.speed
        elif self.direction == EAST:
            self.x += self.speed
        elif self.direction == WEST:
            self.x -= self.speed
            
        self.update_state()

    def draw(self):
        color = LIGHT_BLUE if self.state == APPROACHING else BLUE
        if self.state == CLEARED:
            color = (0, 100, 0)  # Dark green for cleared vehicles
            
        car = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(car, color, (0, 0, self.width, self.height))
        
        # Rotate based on direction
        angle = 0
        if self.direction == EAST:
            angle = 270
        elif self.direction == SOUTH:
            angle = 180
        elif self.direction == WEST:
            angle = 90
            
        rotated = pygame.transform.rotate(car, angle)
        screen.blit(rotated, (self.x - rotated.get_width()//2, self.y - rotated.get_height()//2))

    def is_off_screen(self):
        buffer = 100
        if self.direction == NORTH and self.y < -buffer:
            return True
        elif self.direction == SOUTH and self.y > HEIGHT + buffer:
            return True
        elif self.direction == EAST and self.x > WIDTH + buffer:
            return True
        elif self.direction == WEST and self.x < -buffer:
            return True
        return False

class TrafficLightSystem:
    def __init__(self):
        self.states = [RED] * 4  # One for each direction
        self.yellow_states = [False] * 4
        self.current_green = None
        self.last_change = pygame.time.get_ticks()
        self.min_green_time = 3000  # 3 seconds minimum
        self.max_green_time = 8000  # 8 seconds maximum
        self.yellow_time = 2000     # 2 seconds yellow
        self.traffic_data = []
        self.traffic_labels = []
        self.knn = KNeighborsClassifier(n_neighbors=3)
        self.min_data = 30  # Minimum data points before using KNN
        self.using_knn = False
        
    def get_traffic_density(self, vehicles):
        density = [0] * 4  # One count per direction
        
        for v in vehicles:
            if v.state == APPROACHING:
                if v.direction == NORTH and v.y > INTERSECTION_BOTTOM:
                    density[NORTH] += 1
                elif v.direction == SOUTH and v.y < INTERSECTION_TOP:
                    density[SOUTH] += 1
                elif v.direction == EAST and v.x < INTERSECTION_LEFT:
                    density[EAST] += 1
                elif v.direction == WEST and v.x > INTERSECTION_RIGHT:
                    density[WEST] += 1
                    
        return density
        
    def is_intersection_clear(self, vehicles, exclude_direction=None):
        for v in vehicles:
            if v.state == IN_INTERSECTION and (exclude_direction is None or v.direction != exclude_direction):
                return False
        return True
        
    def update(self, vehicles):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.last_change
        
        # Get current traffic density
        density = self.get_traffic_density(vehicles)
        
        # Store data for KNN training
        if self.current_green is not None:
            self.traffic_data.append(density)
            self.traffic_labels.append(self.current_green)
            if len(self.traffic_data) > 100:  # Keep last 100 data points
                self.traffic_data = self.traffic_data[-100:]
                self.traffic_labels = self.traffic_labels[-100:]
        
        # Check if we should consider changing lights
        if self.current_green is None or elapsed > self.min_green_time:
            intersection_clear = self.is_intersection_clear(vehicles, self.current_green)
            
            # Time to change lights (either max time reached or min time + intersection clear)
            if elapsed > self.max_green_time or (intersection_clear and elapsed > self.min_green_time):
                
                # Switch to KNN once we have enough data
                if len(self.traffic_data) >= self.min_data and not self.using_knn:
                    self.using_knn = True
                
                if self.using_knn:
                    try:
                        # Train KNN with current data
                        self.knn.fit(self.traffic_data, self.traffic_labels)
                        
                        # Get probabilities for each direction
                        proba = self.knn.predict_proba([density])[0]
                        
                        # Calculate scores for each direction
                        scores = []
                        for d in range(4):
                            if d == self.current_green:
                                # Reduce score for current direction to encourage switching
                                scores.append(density[d] * (proba[d] * 0.7))
                            else:
                                # Add small bias to prevent zero scores
                                scores.append(density[d] * (proba[d] + 0.1))
                        
                        # Select direction with highest score
                        next_green = np.argmax(scores)
                    except Exception as e:
                        print(f"KNN Error: {e}")
                        next_green = (self.current_green + 1) % 4 if self.current_green is not None else NORTH
                else:
                    # Simple rotation until we have enough data
                    next_green = (self.current_green + 1) % 4 if self.current_green is not None else NORTH
                
                # Only switch if different direction and intersection is clear
                if next_green != self.current_green and self.is_intersection_clear(vehicles):
                    if self.current_green is not None:
                        # Set current light to yellow
                        self.states[self.current_green] = YELLOW
                        self.yellow_states[self.current_green] = True
                    
                    # Update to new green light
                    self.last_change = current_time
                    self.current_green = next_green
        
        # Update all light states
        for i in range(4):
            if i == self.current_green:
                if elapsed > self.max_green_time - self.yellow_time:
                    self.states[i] = YELLOW
                    self.yellow_states[i] = True
                else:
                    self.states[i] = GREEN
                    self.yellow_states[i] = False
            else:
                self.states[i] = RED
                self.yellow_states[i] = False
    
    def draw_lights(self):
        light_positions = [
            (WIDTH//2, INTERSECTION_TOP - 50),    # North
            (INTERSECTION_RIGHT + 50, HEIGHT//2), # East
            (WIDTH//2, INTERSECTION_BOTTOM + 50), # South
            (INTERSECTION_LEFT - 50, HEIGHT//2)   # West
        ]
        
        for i, pos in enumerate(light_positions):
            # Light box
            pygame.draw.rect(screen, BLACK, (pos[0]-15, pos[1]-45, 30, 90))
            
            # Red light
            pygame.draw.circle(screen, RED if self.states[i] == RED else (50, 0, 0), 
                             (pos[0], pos[1]-30), 10)
            # Yellow light
            pygame.draw.circle(screen, YELLOW if self.states[i] == YELLOW else (50, 50, 0), 
                             (pos[0], pos[1]), 10)
            # Green light
            pygame.draw.circle(screen, GREEN if self.states[i] == GREEN else (0, 50, 0), 
                             (pos[0], pos[1]+30), 10)

def draw_intersection():
    # Draw roads
    pygame.draw.rect(screen, BLACK, (INTERSECTION_LEFT, 0, INTERSECTION_RIGHT-INTERSECTION_LEFT, HEIGHT))
    pygame.draw.rect(screen, BLACK, (0, INTERSECTION_TOP, WIDTH, INTERSECTION_BOTTOM-INTERSECTION_TOP))
    
    # Draw lane markings
    for y in range(0, HEIGHT, 40):
        pygame.draw.rect(screen, WHITE, (WIDTH//2-5, y, 10, 20))
    for x in range(0, WIDTH, 40):
        pygame.draw.rect(screen, WHITE, (x, HEIGHT//2-5, 20, 10))

def main():
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 24)
    
    # Initialize systems
    vehicles = []
    traffic_lights = TrafficLightSystem()
    spawn_timer = 0
    total_crossed = 0
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d:  # Debug info
                    density = traffic_lights.get_traffic_density(vehicles)
                    print("\n--- Traffic Light Debug ---")
                    print(f"Current Green: {['North','East','South','West'][traffic_lights.current_green]}")
                    print(f"Traffic Density: N:{density[NORTH]} E:{density[EAST]} S:{density[SOUTH]} W:{density[WEST]}")
                    print(f"Using KNN: {traffic_lights.using_knn}")
                    print(f"Training Data: {len(traffic_lights.traffic_data)} samples")
        
        # Spawn new vehicles
        spawn_timer += 1
        if spawn_timer >= 15:  # Spawn more frequently to create density
            # Weighted random choice - higher chance for North/South to create asymmetry
            direction = random.choices([NORTH, EAST, SOUTH, WEST], 
                                     weights=[1.5, 1.0, 1.5, 1.0], k=1)[0]
            vehicles.append(Vehicle(0, 0, direction))  # Position will be set in constructor
            spawn_timer = 0
        
        # Update systems
        traffic_lights.update(vehicles)
        
        # Move vehicles
        to_remove = []
        for v in vehicles:
            v.move(traffic_lights.states, traffic_lights.yellow_states)
            if v.is_off_screen():
                to_remove.append(v)
                if v.state == CLEARED:
                    total_crossed += 1
        
        for v in to_remove:
            vehicles.remove(v)
        
        # Draw everything
        screen.fill(GRAY)
        draw_intersection()
        
        # Draw vehicles (sorted by position for proper overlapping)
        for v in sorted(vehicles, key=lambda v: v.y if v.direction in [NORTH, SOUTH] else -v.x):
            v.draw()
        
        traffic_lights.draw_lights()
        
        # Draw stats
        density = traffic_lights.get_traffic_density(vehicles)
        stats = [
            f"Vehicles: {len(vehicles)} | Crossed: {total_crossed}",
            f"North: {density[NORTH]} | East: {density[EAST]}",
            f"South: {density[SOUTH]} | West: {density[WEST]}",
            f"Current Green: {['North','East','South','West'][traffic_lights.current_green if traffic_lights.current_green is not None else 0]}",
            f"Control: {'KNN' if traffic_lights.using_knn else 'Sequential'}",
            "Press D for debug info"
        ]
        
        for i, text in enumerate(stats):
            surf = font.render(text, True, WHITE)
            screen.blit(surf, (10, 10 + i*25))
        
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()