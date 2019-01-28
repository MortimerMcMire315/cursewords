#! /usr/bin/env python3

import collections
import itertools
import string
import sys

import puz

from blessed import Terminal

from characters import *

class Cell:
    def __init__(self, solution, entry=None):
        self.solution = solution

        self.number = None
        if entry:
            self.entry = entry
        else:
            self.entry = " "

    def is_block(self):
        return self.solution == "."

    def is_letter(self):
        return self.solution in string.ascii_uppercase

class Grid:
    def __init__(self, grid_x, grid_y, term):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.term = term

    def load(self, puzfile):
        self.puzfile = puzfile
        self.cells = collections.OrderedDict()

        self.row_count = 15
        self.column_count = 15

        for i in range(self.row_count):
            for j in range(self.column_count):
                self.cells[(j,i)] = Cell(
                        self.puzfile.solution[i * self.row_count + j])

        self.across_words = []
        for i in range(self.row_count):
            current_word = []
            for j in range(self.column_count):
                if self.cells[(j,i)].is_letter():
                    current_word.append((j,i))
                else:
                    self.across_words.append(current_word)
                    current_word = []
            if current_word:
                self.across_words.append(current_word)

        self.down_words = []
        for j in range (self.column_count):
            current_word = []
            for i in range(self.row_count):
                if self.cells[(j,i)].is_letter():
                    current_word.append((j,i))
                else:
                    self.down_words.append(current_word)
                    current_word = []
            if current_word:
                self.down_words.append(current_word)

        num = self.puzfile.clue_numbering()
        self.across_clues = {word['num']:word['clue'] for word in num.across}
        self.down_clues = {word['num']:word['clue'] for word in num.down}

        return None

    def draw(self):
        top_row = self.get_top_row()
        bottom_row = self.get_bottom_row()
        middle_row = self.get_middle_row()
        divider_row = self.get_divider_row()

        print(self.term.move(self.grid_y, self.grid_x) + top_row)
        for index, y_val in enumerate(range(self.grid_y + 1,
                                     self.grid_y + self.row_count * 2), 1):
            if index % 2 == 0:
                print(self.term.move(y_val, self.grid_x) + divider_row)
            else:
                print(self.term.move(y_val, self.grid_x) + middle_row)
        print(self.term.move(self.grid_y + self.row_count * 2, self.grid_x)
              + bottom_row)
       
        return None

    def number(self):
        number = 1
        for x, y in self.cells:
            cell = self.cells[(x,y)]
            if (not cell.is_block() and ((x == 0 or y == 0) or
                                        (self.cells[(x-1, y)].is_block() or
                                        self.cells[(x, y-1)].is_block()))):
                cell.number = number
                number += 1

        return None

    def fill(self):
        for position in self.cells:
            y_coord, x_coord = self.to_term(position)
            cell = self.cells[position]
            if cell.is_letter():
                print(self.term.move(y_coord, x_coord) + cell.entry)
            elif cell.is_block():
                print(self.term.move(y_coord, x_coord - 1) + squareblock)

            if cell.number:
                small = self.small_nums(cell.number)
                x_pos = x_coord - 1
                print(self.term.move(y_coord - 1, x_pos) + small)

        return None

    def to_term(self, position):
        point_x, point_y = position
        term_x = self.grid_x + (4 * point_x) + 2
        term_y = self.grid_y + (2 * point_y) + 1
        return (term_y, term_x)

    def small_nums(self, number):
        small_num = ""
        num_dict = {"1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                    "6": "₆", "7": "₇", "8": "₈", "9": "₉", "0": "₀" }
        for digit in str(number):
            small_num += num_dict[digit]

        return small_num

    def make_row(self, leftmost, middle, divider, rightmost):
        row = leftmost
        for col in range(1, 60):
            new_char = divider if col % 4 == 0 else middle
            row += new_char
        row += rightmost
        return row

    def get_top_row(self):
        return self.make_row(ulcorner, hline, ttee, urcorner)

    def get_bottom_row(self):
        return self.make_row(llcorner, hline, btee, lrcorner)

    def get_middle_row(self):
        return self.make_row(vline, " ", vline, vline)

    def get_divider_row(self):
        return self.make_row(ltee, hline, bigplus, rtee)


class Cursor:
    def __init__(self, position, direction, grid):
        self.position = position
        self.direction = direction
        self.grid = grid

    def switch_direction(self, to=None):
        if to:
            self.direction = to
        elif self.direction == "across":
            self.direction = "down"
        elif self.direction == "down":
            self.direction = "across"

    def advance(self):
        if self.direction == "across":
            self.position = next(self.move_right())
        elif self.direction == "down":
            self.position = next(self.move_down())

    def retreat(self):
        if self.direction == "across":
            self.position = next(self.move_left())
        elif self.direction == "down":
            self.position = next(self.move_up())

    def move_right(self):
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]
        forever_spaces = itertools.cycle(ordered_spaces)

        yield from forever_spaces

    def move_left(self):
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] + 
                          spaces[:current_space:-1])
        forever_spaces = itertools.cycle(ordered_spaces)

        yield from forever_spaces

    def move_down(self):
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]
        forever_spaces = itertools.cycle(ordered_spaces)

        yield from forever_spaces

    def move_up(self):
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] + 
                          spaces[:current_space:-1])
        forever_spaces = itertools.cycle(ordered_spaces)

        yield from forever_spaces

    def current_word(self):
        pos = self.position
        word = []

        if self.direction == "across":
            word = [w for w in self.grid.across_words if pos in w][0] 

        if self.direction == "down":
            word = [w for w in self.grid.down_words if pos in w][0]

        return word

    def is_off_grid(self, pos):
        return (pos[0] < 0 or
                pos[0] >= self.grid.row_count or
                pos[1] < 0 or
                pos[1] >= self.grid.column_count)


def main():
    filename = sys.argv[1]
    try: 
        puzfile = puz.read(filename)
    except:
        sys.exit("Unable to parse {} as a .puz file.".format(filename))

    term = Terminal()

    print(term.enter_fullscreen())
    print(term.clear())

    grid_x = 4
    grid_y = 2

    grid = Grid(grid_x, grid_y, term)
    grid.load(puzfile)
    grid.draw()
    grid.number()
    grid.fill()

    start_pos = grid.across_words[0][0]
    cursor = Cursor(start_pos, "across", grid)

    old_word = []
    old_position = start_pos
    keypress = ''

    with term.cbreak(), term.hidden_cursor():
        while repr(keypress) != 'KEY_ESCAPE':
            # Debugging output here:
            with term.location(0, term.height - 4):
                print(str(repr(keypress) + " " +  str(cursor.position) + " " +
                        str(cursor.current_word())
                        + " " + str(cursor.direction)).ljust(2 * term.width))
            with term.location(0, term.height - 2):
                print("press escape to exit")

            if cursor.direction == "across":
                num = grid.cells.get(cursor.current_word()[0]).number
                clue = grid.across_clues[num]
            elif cursor.direction == "down":
                num = grid.cells.get(cursor.current_word()[0]).number
                clue = grid.down_clues[num]

            compiled = (str(num) + " " + cursor.direction.upper() \
                            + ": " + clue)
            with term.location(4, term.height - 7):
                print(compiled.ljust(term.width))

            if cursor.current_word() is not old_word:
                for position in old_word:
                    print(term.move(*grid.to_term(position)) +
                            grid.cells.get(position).entry)
                for position in cursor.current_word():
                    print(term.move(*grid.to_term(position)) +
                            term.underline(grid.cells.get(position).entry))
            else:
                print(term.move(*grid.to_term(old_position)) +
                        term.underline(grid.cells.get(old_position).entry))

            value = grid.cells.get(cursor.position).entry
            print(term.move(*grid.to_term(cursor.position))
                    + term.reverse(value))

            keypress = term.inkey()

            old_position = cursor.position
            old_word = cursor.current_word()

            if keypress in string.ascii_letters:

                grid.cells.get(cursor.position).entry = keypress.upper()

                cursor.advance()

            elif keypress.name == 'KEY_DELETE':

                grid.cells.get(cursor.position).entry = ' '

                cursor.retreat()

            elif (keypress.name == 'KEY_TAB' or
                    (cursor.direction == "across" and
                        keypress.name in ['KEY_DOWN', 'KEY_UP']) or
                    (cursor.direction == "down" and
                        keypress.name in ['KEY_LEFT', 'KEY_RIGHT'])):

                cursor.switch_direction()

            elif ((cursor.direction == "across" and keypress.name == 'KEY_RIGHT') or
                    (cursor.direction == "down" and keypress.name == 'KEY_DOWN')):

                cursor.advance()

            elif ((cursor.direction == "across" and keypress.name == 'KEY_LEFT') or
                    (cursor.direction == "down" and keypress.name == 'KEY_UP')):

                cursor.retreat()

    print(term.exit_fullscreen())

if __name__ == '__main__':
    main()
