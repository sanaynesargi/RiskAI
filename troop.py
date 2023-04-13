import pygame
import os
import copy


def get_roman_numeral_for_arabic_number(num):
    if 0 < num < 3:
        return "I"
    if 2 < num < 5:
        return "III"
    elif 4 < num < 10:
        return "V"
    elif num >= 10:
        return "X"


def get_circle_color(num):
    if 0 < num < 3:
        return 255, 255, 255
    if 2 < num < 4:
        return 173, 216, 230
    elif 3 < num < 10:
        return 127, 255, 0
    elif num == 10:
        return 255, 255, 0
    elif num > 10:
        return 255, 165, 0
    else:
        return 255, 0, 0


def load_arrow_image(path):
    scaled_image = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (225//4 - 10, 225//4))
    rotated_image = pygame.transform.rotate(scaled_image, 180)

    return rotated_image


class Troop(pygame.sprite.Sprite):
    def __init__(self, window, color, start_pos, number=0, display=False):
        super().__init__()

        self.window = window
        self.display = display
        self.image = None
        self.rect = self.image.get_rect() if self.image else None
        self.x = start_pos[0]
        self.y = start_pos[1]
        self.color = color
        self.number = number
        self.disabled = False
        self.highlight = False
        self.highlight_attack = False
        self.highlight_defend = False
        self.arrow_image = load_arrow_image("./images/arrow.png")
        self.arrow = False

        self._get_image_for_color(color, number, display)

    def __eq__(self, other):
        return self.number == other.number

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if isinstance(v, pygame.Surface):
                setattr(result, k, v)
            elif k == "image" or k == "rect":
                setattr(result, k, v)
            else:
                setattr(result, k, copy.deepcopy(v, memo))
        return result

    def _get_image_for_color(self, color, number, display):
        roman_numeral = get_roman_numeral_for_arabic_number(number)
        divisor = 14 if self.display else 20

        if display and not roman_numeral:
            self.image = pygame.transform.scale(
                pygame.image.load(
                    os.path.join("images", "Troops", color, f"{color} {roman_numeral}.png")).convert_alpha(),
                (500 / divisor, 500 / divisor))
            self.rect = self.image.get_rect()

        elif not roman_numeral:
            return None

        self.image = pygame.transform.scale(
            pygame.image.load(os.path.join("images", "Troops", color, f"{color} {roman_numeral}.png")).convert_alpha(),
            (500 / divisor, 500 / divisor))
        self.rect = self.image.get_rect()

    def _get_number_text(self):
        text = str(self.number)
        font = pygame.font.SysFont("ComicSans", 15, True)

        return font.render(text, True, (0, 0, 0))

    def draw(self):
        if self.number == 0 and not self.display:
            return

        self._get_image_for_color(self.color, self.number, self.display)
        number = self._get_number_text()
        bg_color = ()

        if self.highlight:
            bg_color = (255, 255, 0)
        if self.highlight_attack:
            bg_color = (255, 0, 0)
        elif self.highlight_defend:
            bg_color = (0, 100, 255)
        else:
            bg_color = (255, 255, 255)

        rect_color = bg_color if not self.disabled else (169, 169, 169)
        circle_color = get_circle_color(self.number)

        if self.image and self.rect:
            if not self.display:
                number_offset = -4 if self.number < 10 else -10

                pygame.draw.circle(self.window, circle_color, (self.x + self.rect.width, self.y - 3), 12.5)
                pygame.draw.rect(self.window, rect_color,
                                 pygame.Rect(self.x, self.y, self.rect.width, self.rect.height), 0, 4)

                self.window.blit(number, ((self.x + self.rect.width) + number_offset, self.y - 13.5))
                self.window.blit(self.image, (self.x, self.y))

                if self.arrow:
                    self.window.blit(self.arrow_image, (self.x - 10, self.y + 20))

            else:
                pygame.draw.rect(self.window, rect_color,
                                 pygame.Rect(self.x, self.y, self.rect.width, self.rect.height), 0, 4)
                self.window.blit(self.image, (self.x, self.y))

