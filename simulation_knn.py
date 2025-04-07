import pygame
import random
import math
from collections import defaultdict
import numpy as np
from sklearn.neighbors import KNeighborsRegressor

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Traffic Management with KNN")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
BLUE = (0, 0, 255)

# Directions
NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

# Intersection boundaries
INTERSECTION_TOP = 250
INTERSECTION_BOTTOM = 350
INTERSECTION_LEFT = 300
INTERSECTION_RIGHT = 400

def create_intersection_background():
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill(GRAY)
    
    # Main roads
    pygame.draw.rect(background, BLACK, (INTERSECTION_LEFT, 0, 100, HEIGHT))  # Vertical
    pygame.draw.rect(background, BLACK, (0, INTERSECTION_TOP, WIDTH, 100))    # Horizontal
    
    # Lane markings
    for y in range(0, HEIGHT, 40):
        pygame.draw.rect(background, WHITE, (INTERSECTION_LEFT + 45, y, 10, 20))
    for x in range(0, WIDTH, 40):
        pygame.draw.rect(background, WHITE, (x, INTERSECTION_TOP + 45, 20, 10))
    
    return background

# Load assets
try:
    road_img = pygame.image.load('road.jpg')
    road_img = pygame.transform.scale(road_img, (WIDTH, HEIGHT))
except:
    road_img = create_intersection_background()

# Load car image
try:
    car_img = pygame.image.load('car.png')
    car_img = pygame.transform.scale(car_img, (30, 60))
    car_img = car_img.convert_alpha()
except:
    car_img = pygame.Surface((30, 60), pygame.SRCALPHA)
    pygame.draw.rect(car_img, BLUE, (0, 0, 30, 60))
    print("Using placeholder car image")

class Vehicle:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = random.uniform(2.0, 3.5)
        self.wait_time = 0
        self.has_entered_intersection = False
        self.has_exited_intersection = False
        self.entry_time = 0
        
    def is_in_intersection(self):
        if self.direction in [NORTH, SOUTH]:
            return INTERSECTION_TOP < self.y < INTERSECTION_BOTTOM
        else:
            return INTERSECTION_LEFT < self.x < INTERSECTION_RIGHT
        
    def move(self, traffic_light_state, yellow_light):
        must_stop = False
        
        if traffic_light_state[self.direction] == RED or (
            yellow_light[self.direction] and not self.has_entered_intersection):
            must_stop = True
        
        if not must_stop:
            if self.direction == NORTH:
                self.y -= self.speed
                if not self.has_entered_intersection and self.y < INTERSECTION_BOTTOM:
                    self.has_entered_intersection = True
                    self.entry_time = pygame.time.get_ticks()
                if self.y < INTERSECTION_TOP:
                    self.has_exited_intersection = True
            elif self.direction == EAST:
                self.x += self.speed
                if not self.has_entered_intersection and self.x > INTERSECTION_LEFT:
                    self.has_entered_intersection = True
                    self.entry_time = pygame.time.get_ticks()
                if self.x > INTERSECTION_RIGHT:
                    self.has_exited_intersection = True
            elif self.direction == SOUTH:
                self.y += self.speed
                if not self.has_entered_intersection and self.y > INTERSECTION_TOP:
                    self.has_entered_intersection = True
                    self.entry_time = pygame.time.get_ticks()
                if self.y > INTERSECTION_BOTTOM:
                    self.has_exited_intersection = True
            elif self.direction == WEST:
                self.x -= self.speed
                if not self.has_entered_intersection and self.x < INTERSECTION_RIGHT:
                    self.has_entered_intersection = True
                    self.entry_time = pygame.time.get_ticks()
                if self.x < INTERSECTION_LEFT:
                    self.has_exited_intersection = True
                
            self.wait_time = 0
        else:
            self.wait_time += 1
        
    def draw(self):
        rotated_car = pygame.transform.rotate(car_img, self.direction * -90)
        draw_x = self.x - rotated_car.get_width()//2
        draw_y = self.y - rotated_car.get_height()//2
        screen.blit(rotated_car, (draw_x, draw_y))
        
    def is_off_screen(self):
        buffer = 100
        if self.direction == NORTH and self.y < -buffer:
            return True
        elif self.direction == EAST and self.x > WIDTH + buffer:
            return True
        elif self.direction == SOUTH and self.y > HEIGHT + buffer:
            return True
        elif self.direction == WEST and self.x < -buffer:
            return True
        return False

class TrafficDataCollector:
    def __init__(self):
        self.history = []
        self.current_state = {}
        self.features = []
        self.labels = []
        
    def record_state(self, vehicle_counts, wait_times, current_light):
        self.current_state = {
            'north_count': vehicle_counts[NORTH],
            'east_count': vehicle_counts[EAST],
            'south_count': vehicle_counts[SOUTH],
            'west_count': vehicle_counts[WEST],
            'north_wait': wait_times[NORTH],
            'east_wait': wait_times[EAST],
            'south_wait': wait_times[SOUTH],
            'west_wait': wait_times[WEST],
            'current_light': current_light
        }
        
    def record_outcome(self, vehicles_cleared, avg_wait_time):
        self.current_state['outcome'] = vehicles_cleared * 10 - avg_wait_time
        self.history.append(self.current_state)
        
        features = [
            self.current_state['north_count'],
            self.current_state['east_count'],
            self.current_state['south_count'],
            self.current_state['west_count'],
            self.current_state['north_wait'],
            self.current_state['east_wait'],
            self.current_state['south_wait'],
            self.current_state['west_wait'],
            self.current_state['current_light']
        ]
        self.features.append(features)
        self.labels.append(self.current_state['outcome'])

class KNNTrafficController:
    def __init__(self):
        self.model = KNeighborsRegressor(n_neighbors=3)
        self.is_trained = False
        
    def train(self, features, labels):
        if len(features) > 10:  # Only train once we have enough data
            X = np.array(features)
            y = np.array(labels)
            self.model.fit(X, y)
            self.is_trained = True
            print("KNN model trained with", len(features), "samples")
            
    def predict_best_duration(self, current_state):
        if not self.is_trained:
            return 5000  # Default duration
            
        features = [
            current_state['north_count'],
            current_state['east_count'],
            current_state['south_count'],
            current_state['west_count'],
            current_state['north_wait'],
            current_state['east_wait'],
            current_state['south_wait'],
            current_state['west_wait'],
            current_state['current_light']
        ]
        
        prediction = self.model.predict([features])[0]
        return max(3000, min(10000, 5000 + prediction * 100))  # Keep between 3-10 seconds

class TrafficLightSystem:
    def __init__(self):
        self.states = [RED] * 4
        self.yellow_states = [False] * 4
        self.current_green = None
        self.green_duration = 5000  # Initial default
        self.yellow_duration = 2000
        self.last_change_time = pygame.time.get_ticks()
        self.sequence = [NORTH, EAST, SOUTH, WEST]
        self.data_collector = TrafficDataCollector()
        self.knn_controller = KNNTrafficController()
        self.last_cleared_count = 0
        
    def check_intersection_clear(self, vehicles):
        for vehicle in vehicles:
            if vehicle.is_in_intersection() and vehicle.direction != self.current_green:
                return False
        return True
        
    def update(self, vehicles):
        current_time = pygame.time.get_ticks()
        time_since_change = current_time - self.last_change_time
        
        # Collect current traffic data
        vehicle_counts = defaultdict(int)
        wait_times = defaultdict(int)
        for vehicle in vehicles:
            vehicle_counts[vehicle.direction] += 1
            wait_times[vehicle.direction] += vehicle.wait_time
        
        # Normalize wait times
        for direction in wait_times:
            if vehicle_counts[direction] > 0:
                wait_times[direction] /= vehicle_counts[direction]
        
        self.data_collector.record_state(vehicle_counts, wait_times, self.current_green)
        
        # Check if we should change lights
        if time_since_change > self.green_duration + self.yellow_duration:
            # Calculate how many vehicles cleared during this cycle
            cleared = sum(1 for v in vehicles if v.has_exited_intersection and 
                         v.entry_time > self.last_change_time)
            self.last_cleared_count = cleared
            
            # Calculate average wait time
            avg_wait = sum(wait_times.values()) / 4 if len(wait_times) > 0 else 0
            
            # Record outcome
            self.data_collector.record_outcome(cleared, avg_wait)
            
            # Train/update KNN model
            self.knn_controller.train(self.data_collector.features, 
                                    self.data_collector.labels)
            
            # Change to next light
            if self.current_green is None:
                self.current_green = self.sequence[0]
            else:
                current_index = self.sequence.index(self.current_green)
                self.current_green = self.sequence[(current_index + 1) % 4]
            
            # Get new duration from KNN
            current_state = {
                'north_count': vehicle_counts[NORTH],
                'east_count': vehicle_counts[EAST],
                'south_count': vehicle_counts[SOUTH],
                'west_count': vehicle_counts[WEST],
                'north_wait': wait_times.get(NORTH, 0),
                'east_wait': wait_times.get(EAST, 0),
                'south_wait': wait_times.get(SOUTH, 0),
                'west_wait': wait_times.get(WEST, 0),
                'current_light': self.current_green
            }
            self.green_duration = self.knn_controller.predict_best_duration(current_state)
            self.last_change_time = current_time
        
        # Update light states
        for i in range(4):
            if i == self.current_green:
                if time_since_change > self.green_duration:
                    self.states[i] = YELLOW
                    self.yellow_states[i] = True
                else:
                    self.states[i] = GREEN
                    self.yellow_states[i] = False
            else:
                self.states[i] = RED
                self.yellow_states[i] = False
    
    def draw(self):
        light_positions = [
            (WIDTH//2 - 20, INTERSECTION_TOP - 50),  # North
            (INTERSECTION_RIGHT + 50, HEIGHT//2 - 20),  # East
            (WIDTH//2 + 20, INTERSECTION_BOTTOM + 50),  # South
            (INTERSECTION_LEFT - 50, HEIGHT//2 + 20)   # West
        ]
        
        for i, pos in enumerate(light_positions):
            pygame.draw.rect(screen, BLACK, (pos[0] - 15, pos[1] - 45, 30, 90))
            pygame.draw.circle(screen, RED if self.states[i] == RED else (50, 0, 0), 
                            (pos[0], pos[1] - 30), 10)
            pygame.draw.circle(screen, YELLOW if self.states[i] == YELLOW else (50, 50, 0), 
                            (pos[0], pos[1]), 10)
            pygame.draw.circle(screen, GREEN if self.states[i] == GREEN else (0, 50, 0), 
                            (pos[0], pos[1] + 30), 10)

def main():
    running = True
    clock = pygame.time.Clock()
    vehicles = []
    spawn_timer = 0
    traffic_light_system = TrafficLightSystem()
    font = pygame.font.SysFont('Arial', 20)
    small_font = pygame.font.SysFont('Arial', 16)
    
    # Vehicle counters
    vehicle_counters = {
        NORTH: 0,
        EAST: 0,
        SOUTH: 0,
        WEST: 0
    }
    total_crossed = 0
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Spawn vehicles
        spawn_timer += 1
        if spawn_timer >= 30:
            direction = random.randint(0, 3)
            
            if direction == NORTH:
                x = random.randint(INTERSECTION_LEFT + 30, INTERSECTION_RIGHT - 30)
                y = HEIGHT + 30
            elif direction == EAST:
                x = -30
                y = random.randint(INTERSECTION_TOP + 30, INTERSECTION_BOTTOM - 30)
            elif direction == SOUTH:
                x = random.randint(INTERSECTION_LEFT + 30, INTERSECTION_RIGHT - 30)
                y = -30
            else:  # WEST
                x = WIDTH + 30
                y = random.randint(INTERSECTION_TOP + 30, INTERSECTION_BOTTOM - 30)
                
            vehicles.append(Vehicle(x, y, direction))
            vehicle_counters[direction] += 1
            spawn_timer = 0
        
        traffic_light_system.update(vehicles)
        
        # Move vehicles and remove those that exited
        vehicles_to_remove = []
        for vehicle in vehicles:
            vehicle.move(traffic_light_system.states, traffic_light_system.yellow_states)
            if vehicle.is_off_screen():
                vehicles_to_remove.append(vehicle)
                if vehicle.has_exited_intersection:
                    total_crossed += 1
        
        for vehicle in vehicles_to_remove:
            vehicles.remove(vehicle)
        
        # Draw everything
        screen.blit(road_img, (0, 0))
        
        # Sort vehicles by position (those further back drawn first)
        vehicles_sorted = sorted(vehicles, key=lambda v: (
            -v.y if v.direction == NORTH else
            v.x if v.direction == EAST else
            v.y if v.direction == SOUTH else
            -v.x
        ))
        
        # Draw vehicles in correct order
        for vehicle in vehicles_sorted:
            vehicle.draw()
        
        # Draw traffic lights (always on top)
        traffic_light_system.draw()
        
        # Update counters
        current_counts = {
            NORTH: len([v for v in vehicles if v.direction == NORTH]),
            EAST: len([v for v in vehicles if v.direction == EAST]),
            SOUTH: len([v for v in vehicles if v.direction == SOUTH]),
            WEST: len([v for v in vehicles if v.direction == WEST])
        }
        
        # Calculate average wait times
        wait_times = defaultdict(int)
        for vehicle in vehicles:
            wait_times[vehicle.direction] += vehicle.wait_time
        for direction in wait_times:
            if current_counts[direction] > 0:
                wait_times[direction] /= current_counts[direction]
        
        # Display stats
        current_green = traffic_light_system.current_green if traffic_light_system.current_green is not None else -1
        green_text = ["NORTH", "EAST", "SOUTH", "WEST"][current_green] if current_green != -1 else "NONE"
        
        stats = [
            f"Vehicles: {len(vehicles)} | Crossed: {total_crossed} | Last Cycle Cleared: {traffic_light_system.last_cleared_count}",
            f"Green Light: {green_text} | Duration: {traffic_light_system.green_duration/1000:.1f}s",
            f"North: {current_counts[NORTH]} (Wait: {wait_times.get(NORTH, 0):.1f})",
            f"East: {current_counts[EAST]} (Wait: {wait_times.get(EAST, 0):.1f})",
            f"South: {current_counts[SOUTH]} (Wait: {wait_times.get(SOUTH, 0):.1f})",
            f"West: {current_counts[WEST]} (Wait: {wait_times.get(WEST, 0):.1f})",
            f"KNN Model: {'Trained' if traffic_light_system.knn_controller.is_trained else 'Training...'}",
            f"Data Samples: {len(traffic_light_system.data_collector.features)}"
        ]
        
        for i, stat in enumerate(stats):
            text = font.render(stat, True, WHITE) if i < 2 else small_font.render(stat, True, WHITE)
            screen.blit(text, (10, 10 + i * 25))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()