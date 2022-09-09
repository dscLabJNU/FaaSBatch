import numpy as np
import time


def look_busy():
    image = np.ones((200, 200))
    # Make your orig array (skipping the extra dimensions).
    orig = np.random.rand(4, 1600)
    # Make its coordinates; x is horizontal.
    x = np.linspace(0, image.shape[1], orig.shape[1])
    y = np.linspace(0, image.shape[0], orig.shape[0])


def main(args=None):
    if not args:
        duration = globals().get('duration', 2)
    else:
        duration = args.get('duration', 2)
    start = time.time()

    while time.time() - start < duration:
        look_busy()

    return {"res": "ok"}
