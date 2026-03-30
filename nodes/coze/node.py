import random
import string

class Node:
    def __init__(self, x: int, y: int):
        self.id = '1' + ''.join(random.choices(string.digits, k=5))

        self.x = x
        self.y = y

    