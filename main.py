import math
import random
import shutil
import keyboard
import pyautogui
from mss import mss
import cv2
import numpy as np
import time
import os
from concurrent.futures import ThreadPoolExecutor

# Define screen capture bounding box
screen_bbox = {'top': 670,
               'left': 1636,
               'width': 570,
               'height': 512}

screen_bbox = {'top': 960,
               'left': 1814,
               'width': 700,
               'height': 532}

# Define pixel positions within the bounding box (relative coordinates)
pixel_position_anchor = (72, 990 - screen_bbox['top'])
anchor_horizontal_gap = 144

pixel_position_anchor = (int(174/2), 1100 - screen_bbox['top'])
anchor_horizontal_gap = 174

pixel_positions = [
    (pixel_position_anchor[0] + anchor_horizontal_gap * 0, pixel_position_anchor[1]),
    (pixel_position_anchor[0] + anchor_horizontal_gap * 1, pixel_position_anchor[1]),
    (pixel_position_anchor[0] + anchor_horizontal_gap * 2, pixel_position_anchor[1]),
    (pixel_position_anchor[0] + anchor_horizontal_gap * 3, pixel_position_anchor[1]),
]

# Key mapping and timing settings
key_mapping = ["f", "g", "h", "j"]
press_delay = 0.1  # Delay to avoid accidental rapid re-press
hold_duration = 5.0  # Maximum time to hold the key down before releasing

# Track last press times and states for each key
last_press_time = [0] * len(key_mapping)
press_state = {key: {"pressed": False, "press_time": 0} for key in key_mapping}

# Initialize mss for faster screen capture
sct = mss()
song_counter = 0


def handle_key_press(index, press_delay_=press_delay):
    key = key_mapping[index]
    current_time = time.time()

    if current_time - press_state[key]["press_time"] <= press_delay_:
        return

    # Press the key if a tile is detected
    keyboard.release(key)
    keyboard.press(key)
    press_state[key]["pressed"] = True
    press_state[key]["press_time"] = current_time
    # print(f"{key.upper()}")


def auto_release_long_pressed_keys():
    """Automatically release keys if they have been held for more than `hold_duration`."""
    current_time = time.time()
    for key in key_mapping:
        if press_state[key]["pressed"] and current_time - press_state[key]["press_time"] >= hold_duration:
            keyboard.release(key)
            press_state[key]["pressed"] = False
            # print(f"{key} automatically released after {hold_duration}s hold")


def debug_save_pixels_vision(img, pixels, index, text=None):
    # Annotate the screen image with circles and color values
    dot_color = (255, 255, 255)
    if text is not None:
        dot_color = (255, 0, 0)

    for (px, py, color) in pixels:
        # Draw a small white circle at each pixel position
        cv2.circle(img, (px, py), 5, dot_color, -1)

        # Write the RGB color value above each circle
        _text = f"{color[0]}, {color[1]}, {color[2]}"
        text_position = (px - 10, py - 10)  # Position text slightly above the pixel
        cv2.putText(img, _text, text_position, cv2.FONT_HERSHEY_SIMPLEX, 0.3, dot_color, 1)

    if text is not None:
        cv2.putText(img, text, (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 1)

    # Save the annotated image as a lossless PNG
    save_path = f"img/vision/frame_{int(time.time() * 1000)}_{index}.png"
    cv2.imwrite(save_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    if text is not None:
        print(f"Saved annotated frame to {save_path}")


def is_single_tile(pixels):
    single_tile_color = [11, 10, 9]
    """Check if the majority of pixels match the given single_tile_color."""
    match_count = sum(1 for _, _, color in pixels if list(color) == single_tile_color)
    return match_count >= len(pixels) - 1


# from StackOverflow
def get_euclidean_color_distance_unnormalized(color1, color2):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def is_matching_color(pixels, target_color, threshold_pixel_square_distance=20):
    """Check if no more than 1 pixel in 'pixels' has a color distance to 'target_color' above 'threshold'."""
    mismatch_count = 0

    for _, _, color in pixels:
        # Check color distance
        if get_euclidean_color_distance_unnormalized(tuple(map(int, color)),
                                                     target_color) >= threshold_pixel_square_distance:
            mismatch_count += 1
            # Return False immediately if there’s more than 1 mismatch
            if mismatch_count > 1:
                return False

    # DEBUG
    # for _, _, color in pixels:
    # Check color distance
    # d = get_euclidean_color_distance_unnormalized(tuple(map(int, color)), target_color)
    # print(f"{tuple(map(int, color))} <> {target_color} => {int(d)}")

    # Return True if there’s 0 or 1 mismatch
    return True


def is_long_tile(pixels):
    return is_matching_color(pixels, (9, 11, 13), threshold_pixel_square_distance=30)


def is_purple_tile(pixels):
    return is_matching_color(pixels, (221, 53, 121), threshold_pixel_square_distance=30)


def recognize_column(index, screen_img):
    """Recognize if a black tile is in the specified column and handle key press."""
    x, y = pixel_positions[index]

    # Define positions of pixels to check around the target (x, y)
    arr_pos = []
    y_offset = 0
    horizontal_padding = 30
    vertical_padding = 10

    # Main idea: 5 pixels
    arr_pos.append((x - horizontal_padding, y - vertical_padding + y_offset))
    arr_pos.append((x + horizontal_padding, y - vertical_padding + y_offset))
    arr_pos.append((x - horizontal_padding, y + vertical_padding + y_offset))
    arr_pos.append((x + horizontal_padding, y + vertical_padding + y_offset))
    arr_pos.append((x, y + y_offset))

    pixels = []
    for p in arr_pos:
        color = screen_img[p[1], p[0]]
        pixels.append((p[0], p[1], color))

    # SINGLE TILE
    if is_single_tile(pixels):
        # SINGLE
        handle_key_press(index)
        # DEBUG
        # debug_save_pixels_vision(screen_img.copy(), pixels, index, "SINGLE")
    elif is_long_tile(pixels):
        # LONG
        handle_key_press(index)
        # DEBUG
        # debug_save_pixels_vision(screen_img.copy(), pixels, index, "LONG")
    elif is_purple_tile(pixels):
        # LONG
        handle_key_press(index)
        # DEBUG
        # debug_save_pixels_vision(screen_img.copy(), pixels, index, "PURPLE")
    else:
        # DEBUG
        # debug_save_pixels_vision(screen_img.copy(), pixels, index)
        pass


def clear_folder(folder_path):
    """Completely delete everything inside the specified folder."""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")


def check_if_next_song_is_available(screen_img):
    global song_counter
    """Check specified pixels and press space if conditions are met."""
    # Define target pixel colors
    target_color_1 = [0, 191, 255]
    target_color_2 = [0, 189, 255]

    # Get the colors of the specified pixels
    pixel_1_color = tuple(map(int, screen_img[495, 217]))  # Convert np.uint8 to int
    pixel_2_color = tuple(map(int, screen_img[498, 349]))  # Convert np.uint8 to int

    # Check if the colors match the target colors
    if pixel_1_color == tuple(target_color_1) and pixel_2_color == tuple(target_color_2):
        # Perform left-click on pixel 1 coordinates three times with a 500ms delay
        # for _ in range(3):
        #     pyautogui.click([1926, 1200])  # Left click at button "NEXT SONG"
        #     time.sleep(0.5)j

        # Press space three times with a 500ms delay
        for _ in range(3):
            keyboard.press_and_release('space')
            time.sleep(0.5)

        song_counter += 1
        print(f"Completed song #{song_counter}")


# Ensure directory exists for saving vision frames
clear_folder("img")
os.makedirs("img/vision", exist_ok=True)

frame_count = 0
start_time = time.time()
time.sleep(0.5)

with ThreadPoolExecutor() as executor:
    while True:
        # Capture screen region
        screen = sct.grab(screen_bbox)
        screen_img = np.array(screen)[:, :, :3]

        # Execute the check function
        if random.randint(0, 50) == 1:
            check_if_next_song_is_available(screen_img)

        # If stuck or failed: Press space
        if random.randint(0, 1500) == 1:
            keyboard.press_and_release('space')

        # Process each column in a separate thread
        futures = [executor.submit(recognize_column, i, screen_img) for i in range(len(pixel_positions))]

        # Wait for all threads to complete
        for future in futures:
            future.result()

        # Check and release keys that have been held down for too long
        auto_release_long_pressed_keys()

        # Calculate and print FPS every second for DEBUG
        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1.0:
            fps = frame_count / elapsed_time
            # print(f"FPS: {fps:.2f}")
            start_time = time.time()
            frame_count = 0
