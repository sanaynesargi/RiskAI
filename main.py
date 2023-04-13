import pygame
import os

from widgets import Widgets
from Game import RiskGame
from troop import Troop
from pygame import mixer

pygame.init()

TURNS = 50
S_WIDTH = 1500
S_HEIGHT = 800

WINDOW = pygame.display.set_mode((S_WIDTH, S_HEIGHT))
STATIC_IMAGES = {
    "background": (
        pygame.transform.scale(pygame.image.load("./images/board.png").convert(), (S_WIDTH * 0.75, S_HEIGHT)),
        (0, 0))
}


def get_troop_selectors(troop_dir_path):
    troops = {}

    startx = 1500
    starty = 20
    xinc = 50
    yinc = 80

    for color in os.listdir(troop_dir_path):
        if ".DS_Store" == color:
            continue

        troops[color] = {}
        startx = 1150

        image_paths = os.listdir(os.path.join(troop_dir_path, color))
        sorted_image_dict = {}

        for path in image_paths:
            troop_type = path.split(" ")[-1][:-4]
            sorted_image_dict[troop_type] = path
        sorted_image_paths = [
            sorted_image_dict["I"],
            sorted_image_dict["III"],
            sorted_image_dict["V"],
            sorted_image_dict["X"]
        ]

        troop_types = [1, 3, 5, 10]
        index = 0
        for image_path in sorted_image_paths:
            troop_type = image_path.split(" ")[-1].split(".")[0]
            image_full_path = os.path.join(os.path.join(troop_dir_path, color), image_path)
            troops[color][troop_type] = Troop(WINDOW, color, (startx, starty), display=True, number=troop_types[index])
            index += 1
            startx += xinc
        starty += yinc

    return troops


WIDGETS = Widgets(WINDOW, (1180, 530), pygame.mouse.get_pos(), [])
TROOPS = get_troop_selectors("./images/Troops")


def draw_player_text():
    color = ["Black", "Red", "Green", "Light Blue"][GAME.PLAYER]
    text = "Turn: "
    font = pygame.font.SysFont("ComicSans", 35, True)

    window_text = font.render(text, False, (255, 255, 255))
    WINDOW.blit(window_text, (1150, 315))

    display_troop = Troop(WINDOW, color, (1250, 325), number=1, display=True)
    display_troop.draw()

    for c in TROOPS.keys():
        for _, troop in TROOPS[c].items():
            if c == color:
                troop.disabled = False
                continue
            troop.disabled = True


def update_ui_callback():
    WIDGETS.draw()

    draw_player_text()

    for color in TROOPS.keys():
        for _, troop in TROOPS[color].items():
            troop.draw()


GAME = RiskGame(WINDOW, STATIC_IMAGES["background"][0], update_ui_callback)
MUSIC = True

if MUSIC:
    mixer.music.load(os.path.join("music", "track1.mp3"))

    # Setting the volume
    mixer.music.set_volume(0.7)

    # Start playing the song
    mixer.music.play()


def draw():
    WINDOW.fill((0, 0, 0))

    pos = pygame.mouse.get_pos()
    WIDGETS.update_mouse_pos(pos)
    WIDGETS.update_territories_owned(GAME.TERRITORIES_OWNED)
    WIDGETS.draw()

    GAME.draw()

    pygame.display.update()


def main():
    pygame.display.set_caption("Risk Game")

    run = True
    while run:

        draw()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    run = False
                elif event.key == pygame.K_LEFT:
                    GAME.run_place_troops()
                elif event.key == pygame.K_RIGHT:
                    # GAME.run_attack_turns()
                    for i in range(TURNS * 4):
                        GAME.find_best_move(["Red", "Light Blue", "Green", "Black"][GAME.PLAYER])

                # music controls
                if MUSIC:
                    if event.key == pygame.K_p:
                        # Pausing the music
                        mixer.music.pause()
                    elif event.key == pygame.K_r:
                        # Resuming the music
                        mixer.music.unpause()
                    elif event.key == pygame.K_e:
                        # Stop the mixer
                        mixer.music.rewind()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                WIDGETS.handle_clicks()


if __name__ == "__main__":
    main()
