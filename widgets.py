import pygame


class Button:
    def __init__(self, surface, color, position, w, h, radius, mouse_pos, text, alt):
        self.surface = surface
        self.original_color = color
        self.color = color
        self.x, self.y = position
        self.w, self.h = w, h
        self.radius = radius
        self.text = text
        self.alternate_text = alt
        self.font = pygame.font.SysFont("ComicSans", 22)
        self.mx, self.my = mouse_pos
        self.mode = True

    def _monitor_hover(self):
        result = self._check_bounding_box()

        if result:
            self.color = (84, 110, 122)
        else:
            self.color = self.original_color

    def _check_bounding_box(self):
        if self.mx < self.x or self.mx > self.x + self.w:
            return False

        if self.my < self.y or self.my > self.y + self.h:
            return False

        return True

    def handle_click(self):
        result = self._check_bounding_box()

        if not result:
            return

        temp = self.alternate_text
        self.alternate_text = self.text
        self.text = temp
        self.mode = not self.mode

    def update_mouse_pos(self, pos):
        self.mx, self.my = pos

    def draw(self):
        self._monitor_hover()

        render = self.font.render(self.text, True, (255, 255, 255))
        render_rect = render.get_rect()

        render_width = render_rect.width
        render_height = render_rect.height
        text_offset_x = (self.x + self.w // 2) - render_width // 2
        text_offset_y = ((self.y + self.h // 2) - render_height // 2) - 2.5

        pygame.draw.rect(self.surface, self.color, (self.x, self.y, self.w, self.h), 0, self.radius)
        self.surface.blit(render, (text_offset_x, text_offset_y))


class Widgets:

    def __init__(self, surface, position, mouse_pos, territories_owned):
        self.surface = surface
        self.x, self.y = position
        self.mx, self.my = mouse_pos
        self.switch_button = Button(surface, (55, 71, 79), (self.x+35, self.y - 50), 175, 40, 40, mouse_pos,
                                    "Show Bonuses", "Show Counts")
        self.territories_owned = territories_owned

    def update_mouse_pos(self, pos):
        self.mx, self.my = pos
        self.switch_button.update_mouse_pos(pos)

    def handle_clicks(self):
        self.switch_button.handle_click()

    def update_territories_owned(self, d):
        self.territories_owned = d

    def _draw_bonuses(self):
        pygame.draw.rect(self.surface, (169, 169, 169), (self.x, self.y, 250, 250), 0, 8)

        bonuses = {"NA": 5, "SA": 2, "EU": 5, "AF": 3, "AS": 7, "AU": 2}

        y_inc = 10
        for continent, bonus in bonuses.items():
            text = f"{continent}: {bonus} Bonus Troops"
            font = pygame.font.SysFont("ComicSans", 20)
            rendered_text = font.render(text, True, (0, 0, 0))

            self.surface.blit(rendered_text, (self.x + 10, self.y + y_inc))
            y_inc += 40

    def _draw_counts(self):
        pygame.draw.rect(self.surface, (143, 169, 175), (self.x, self.y, 250, 250), 0, 8)

        y_inc = 20
        for color, territories in self.territories_owned.items():
            text = f"{color}: {len(territories)} Territories"
            font = pygame.font.SysFont("ComicSans", 20)
            rendered_text = font.render(text, True, (0, 0, 0))

            self.surface.blit(rendered_text, (self.x + 10, self.y + y_inc))
            y_inc += 60

    def draw(self):
        self.switch_button.draw()

        if self.switch_button.mode:
            self._draw_bonuses()
        else:
            self._draw_counts()

