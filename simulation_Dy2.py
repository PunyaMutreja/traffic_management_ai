import pygame
import random
from collections import defaultdict

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AI Traffic Management Simulation")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)

# Directions
NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

# Intersection boundaries
INTERSECTION_TOP = 250
INTERSECTION_BOTTOM = 450
INTERSECTION_LEFT = 300
INTERSECTION_RIGHT = 500

def create_intersection_background():
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill(GRAY)
    
    # Main roads
    pygame.draw.rect(background, BLACK, (INTERSECTION_LEFT, 0, 200, HEIGHT))  # Vertical
    pygame.draw.rect(background, BLACK, (0, INTERSECTION_TOP, WIDTH, 200))    # Horizontal
    
    # Lane markings
    for y in range(0, HEIGHT, 40):
        pygame.draw.rect(background, WHITE, (395, y, 10, 20))
    for x in range(0, WIDTH, 40):
        pygame.draw.rect(background, WHITE, (x, 345, 20, 10))
    
    return background

# Load assets
try:
    road_img = pygame.image.load('road.jpg')
    road_img = pygame.transform.scale(road_img, (WIDTH, HEIGHT))
except:
    road_img = create_intersection_background()

# Load car image - REPLACE 'car.png' WITH YOUR IMAGE FILENAME
try:
    car_img = pygame.image.load('car1.png')
    car_img = pygame.transform.scale(car_img, (40, 80))
    car_img = car_img.convert_alpha()
except:
    car_img = pygame.Surface((40, 80), pygame.SRCALPHA)
    pygame.draw.rect(car_img, (0, 0, 255, 200), (0, 0, 40, 80))
    print("Couldn't load car image, using placeholder")

class Vehicle:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = random.uniform(2.0, 3.5)
        self.wait_time = 0
        self.has_entered_intersection = False
        self.has_exited_intersection = False
        
    def is_in_intersection(self):
        if self.direction in [NORTH, SOUTH]:
            return INTERSECTION_TOP < self.y < INTERSECTION_BOTTOM
        else:
            return INTERSECTION_LEFT < self.x < INTERSECTION_RIGHT
        
    def move(self, traffic_light_state, yellow_light):
        # Check if we need to stop
        must_stop = False
        
        if traffic_light_state[self.direction] == RED or (
            yellow_light[self.direction] and not self.has_entered_intersection):
            must_stop = True
        
        if not must_stop:
            if self.direction == NORTH:
                self.y -= self.speed
                if not self.has_entered_intersection and self.y < INTERSECTION_BOTTOM:
                    self.has_entered_intersection = True
                if self.y < INTERSECTION_TOP:
                    self.has_exited_intersection = True
            elif self.direction == EAST:
                self.x += self.speed
                if not self.has_entered_intersection and self.x > INTERSECTION_LEFT:
                    self.has_entered_intersection = True
                if self.x > INTERSECTION_RIGHT:
                    self.has_exited_intersection = True
            elif self.direction == SOUTH:
                self.y += self.speed
                if not self.has_entered_intersection and self.y > INTERSECTION_TOP:
                    self.has_entered_intersection = True
                if self.y > INTERSECTION_BOTTOM:
                    self.has_exited_intersection = True
            elif self.direction == WEST:
                self.x -= self.speed
                if not self.has_entered_intersection and self.x < INTERSECTION_RIGHT:
                    self.has_entered_intersection = True
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

class TrafficLightSystem:
    def __init__(self):
        self.states = [RED] * 4
        self.yellow_states = [False] * 4
        self.current_green = None
        self.green_duration = 5000
        self.yellow_duration = 2000
        self.last_change_time = pygame.time.get_ticks()
        self.sequence = [NORTH, EAST, SOUTH, WEST]
        self.intersection_clear = True
        
    def check_intersection_clear(self, vehicles):
        for vehicle in vehicles:
            if vehicle.is_in_intersection() and vehicle.direction != self.current_green:
                return False
        return True
        
    def update(self, vehicles):
        current_time = pygame.time.get_ticks()
        time_since_change = current_time - self.last_change_time
        
        self.intersection_clear = self.check_intersection_clear(vehicles)
        
        if time_since_change > self.green_duration + self.yellow_duration or (
            time_since_change > self.green_duration + self.yellow_duration + 2000 and not self.intersection_clear):
            
            if self.current_green is None:
                self.current_green = self.sequence[0]
            else:
                current_index = self.sequence.index(self.current_green)
                self.current_green = self.sequence[(current_index + 1) % 4]
            self.last_change_time = current_time
        
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
            (WIDTH//2 - 20, INTERSECTION_TOP - 70),
            (INTERSECTION_RIGHT + 70, HEIGHT//2 - 20),
            (WIDTH//2 + 20, INTERSECTION_BOTTOM + 70),
            (INTERSECTION_LEFT - 70, HEIGHT//2 + 20)
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
    font = pygame.font.SysFont('Arial', 24)
    
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
                x = random.randint(INTERSECTION_LEFT + 50, INTERSECTION_RIGHT - 50)
                y = HEIGHT + 30
            elif direction == EAST:
                x = -30
                y = random.randint(INTERSECTION_TOP + 50, INTERSECTION_BOTTOM - 50)
            elif direction == SOUTH:
                x = random.randint(INTERSECTION_LEFT + 50, INTERSECTION_RIGHT - 50)
                y = -30
            else:  # WEST
                x = WIDTH + 30
                y = random.randint(INTERSECTION_TOP + 50, INTERSECTION_BOTTOM - 50)
                
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
        
        # Display stats
        current_green = traffic_light_system.current_green if traffic_light_system.current_green is not None else -1
        green_text = ["NORTH", "EAST", "SOUTH", "WEST"][current_green] if current_green != -1 else "NONE"
        stats = [
            f"Vehicles: {len(vehicles)}",
            f"Green Light: {green_text}",
            f"Intersection Clear: {'YES' if traffic_light_system.intersection_clear else 'NO'}",
            f"North: {current_counts[NORTH]} (Entered: {vehicle_counters[NORTH]})",
            f"East: {current_counts[EAST]} (Entered: {vehicle_counters[EAST]})",
            f"South: {current_counts[SOUTH]} (Entered: {vehicle_counters[SOUTH]})",
            f"West: {current_counts[WEST]} (Entered: {vehicle_counters[WEST]})",
            f"Total Crossed: {total_crossed}"
        ]
        
        for i, stat in enumerate(stats):
            text = font.render(stat, True, WHITE)
            screen.blit(text, (10, 10 + i * 25))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()