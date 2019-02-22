#! /usr/bin/env python3

import collections
import itertools
import string
import sys
import textwrap
import threading

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

        self.marked_wrong = False

    def __str__(self):
        return self.entry

    def is_block(self):
        return self.solution == "."

    def is_letter(self):
        return self.solution in string.ascii_uppercase

    def is_blank(self):
        return self.entry == " "

    def is_correct(self):
        return self.entry == self.solution or self.is_block()


class Grid:
    def __init__(self, grid_x, grid_y, term):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.term = term

        self.notification_area = (term.height-2, self.grid_x)

    def load(self, puzfile):
        self.puzfile = puzfile
        self.cells = collections.OrderedDict()
        self.row_count = puzfile.height
        self.column_count = puzfile.width

        self.title = puzfile.title
        self.author = puzfile.author

        for i in range(self.row_count):
            for j in range(self.column_count):
                idx = i * self.column_count + j
                entry = self.puzfile.fill[idx]
                entry = entry if entry.isalnum() else None
                self.cells[(j,i)] = Cell(
                        self.puzfile.solution[idx],
                        entry)

        self.across_words = []
        for i in range(self.row_count):
            current_word = []
            for j in range(self.column_count):
                if self.cells[(j,i)].is_letter():
                    current_word.append((j,i))
                elif current_word:
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
                elif current_word:
                    self.down_words.append(current_word)
                    current_word = []
            if current_word:
                self.down_words.append(current_word)

        self.down_words_grouped = sorted(self.down_words,
                key=lambda word: (word[0][1], word[0][0]))

        num = self.puzfile.clue_numbering()
        self.across_clues = [word['clue'] for word in num.across]
        self.down_clues = [word['clue'] for word in num.down]

        return None

    def draw(self):
        top_row = self.get_top_row()
        bottom_row = self.get_bottom_row()
        middle_row = self.get_middle_row()
        divider_row = self.get_divider_row()

        print(self.term.move(self.grid_y, self.grid_x) +
                self.term.dim(top_row))
        for index, y_val in enumerate(range(self.grid_y + 1,
                                     self.grid_y + self.row_count * 2), 1):
            if index % 2 == 0:
                print(self.term.move(y_val, self.grid_x) +
                        self.term.dim(divider_row))
            else:
                print(self.term.move(y_val, self.grid_x) +
                        self.term.dim(middle_row))
        print(self.term.move(self.grid_y + self.row_count * 2, self.grid_x)
              + self.term.dim(bottom_row))

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
                self.draw_cell(position)
            elif cell.is_block():
                print(self.term.move(y_coord, x_coord - 1) +
                        self.term.dim(squareblock))

            if cell.number:
                small = self.small_nums(cell.number)
                x_pos = x_coord - 1
                print(self.term.move(y_coord - 1, x_pos) + small)

        return None

    def save(self, filename):
        fill = ''
        for pos in self.cells:
            cell = self.cells[pos]
            if cell.is_block():
                entry = "."
            elif cell.entry == " ":
                entry = "-"
            else:
                entry = cell.entry
            fill += entry
        self.puzfile.fill = fill
        self.puzfile.save(filename)

        self.send_notification("Current puzzle state saved!")

    def check_puzzle(self):
        self.send_notification("Checking puzzle for errors.")
        for pos in self.cells:
            cell = self.cells.get(pos)
            if not cell.is_blank() and not cell.is_correct():
                cell.marked_wrong = True
                self.draw_cell(pos)

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
        for col in range(1, self.column_count * 4):
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

    def compile_cell(self, position):
        cell = self.cells.get(position)
        value = cell.entry

        if cell.marked_wrong:
            value = self.term.red(value.lower())

        value = self.term.bold(value)

        return value

    def draw_cell(self, position):
        value = self.compile_cell(position)
        print(self.term.move(*self.to_term(position)) + value)

    def draw_highlighted_cell(self, position):
        value = self.compile_cell(position)
        value = self.term.underline(value)
        print(self.term.move(*self.to_term(position)) + value)

    def draw_cursor_cell(self, position):
        value = self.compile_cell(position)
        value = self.term.reverse(value)
        print(self.term.move(*self.to_term(position)) + value)

    def send_notification(self, message, time=5):
        timer = threading.Timer(time, self.clear_notification_area)
        timer.daemon = True
        print(self.term.move(*self.notification_area)
                + self.term.reverse(message) + self.term.clear_eol)
        timer.start()

    def clear_notification_area(self):
        print(self.term.move(*self.notification_area) + self.term.clear_eol)


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
            self.position = self.move_right()
        elif self.direction == "down":
            self.position = self.move_down()

    def retreat(self):
        if self.direction == "across":
            self.position = self.move_left()
        elif self.direction == "down":
            self.position = self.move_up()

    def advance_within_word(self, overwrite_mode=False, no_wrap_mode=False):
        within_pos = self.move_within_word(overwrite_mode, no_wrap_mode)
        if within_pos:
            self.position = within_pos
        else:
            self.advance_to_next_word(blank_placement=True)

    def move_within_word(self, overwrite_mode=False, no_wrap_mode=False):
        word_spaces = self.current_word()
        current_space = word_spaces.index(self.position)
        ordered_spaces = word_spaces[current_space + 1:]
        if not no_wrap_mode:
            ordered_spaces += word_spaces[:current_space]
        if not overwrite_mode:
            ordered_spaces = [pos for pos in ordered_spaces
                    if self.grid.cells.get(pos).entry == " "]

        return next(iter(ordered_spaces), None)

    def retreat_within_word(self, end_placement=False, blank_placement=False):
        pos_index = self.current_word().index(self.position)
        earliest_blank = self.earliest_blank_in_word()

        if (blank_placement and
                earliest_blank and
                self.position != earliest_blank):
            self.position = earliest_blank
        elif not blank_placement and pos_index > 0:
            self.position = self.current_word()[pos_index - 1]
        else:
            self.retreat_to_previous_word(end_placement, blank_placement)

    def advance_to_next_word(self, blank_placement=False):
        if self.direction == "across":
            word_group = self.grid.across_words
            next_words = self.grid.down_words_grouped
        elif self.direction == "down":
            word_group = self.grid.down_words_grouped
            next_words = self.grid.across_words

        word_index = word_group.index(self.current_word())

        if word_index == len(word_group) - 1:
            self.switch_direction()
            self.position = next_words[0][0]
        else:
            self.position = word_group[word_index + 1][0]

        earliest_blank = self.earliest_blank_in_word()

        # If there are no blank squares left, override
        # the blank_placement setting
        if (blank_placement and
                not any(self.grid.cells.get(pos).entry == ' ' for
                pos in itertools.chain(*self.grid.across_words))):
            blank_placement = False

        # Otherwise, if blank_placement is on, put the
        # cursor in the earliest available blank spot not
        # in the current word
        if blank_placement and earliest_blank:
            self.position = earliest_blank
        elif blank_placement and not earliest_blank:
            self.advance_to_next_word(blank_placement)

    def retreat_to_previous_word(self, end_placement=False, blank_placement=False):
        if self.direction == "across":
            word_group = self.grid.across_words
            next_words = self.grid.down_words_grouped
        elif self.direction == "down":
            word_group = self.grid.down_words_grouped
            next_words = self.grid.across_words

        word_index = word_group.index(self.current_word())

        pos = -1 if end_placement else 0

        if word_index == 0:
            self.switch_direction()
            self.position = next_words[-1][pos]
        else:
            new_word = word_group[word_index - 1]
            self.position = word_group[word_index -1][pos]

        # If there are no blank squares left, override
        # the blank_placement setting
        if (blank_placement and
                not any(self.grid.cells.get(pos).entry == ' ' for
                pos in itertools.chain(*self.grid.across_words))):
            blank_placement = False

        if blank_placement and self.earliest_blank_in_word():
            self.position = self.earliest_blank_in_word()
        elif blank_placement and not self.earliest_blank_in_word():
            self.retreat_to_previous_word(end_placement, blank_placement)

    def earliest_blank_in_word(self):
        blanks = [pos for pos in self.current_word()
                    if self.grid.cells.get(pos).entry == ' ']
        return next(iter(blanks), None)

    def move_right(self):
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_left(self):
        spaces = list(itertools.chain(*self.grid.across_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] + 
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def move_down(self):
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = spaces[current_space + 1:] + spaces[:current_space]

        return next(iter(ordered_spaces))

    def move_up(self):
        spaces = list(itertools.chain(*self.grid.down_words))
        current_space = spaces.index(self.position)
        ordered_spaces = (spaces[current_space - 1::-1] + 
                          spaces[:current_space:-1])

        return next(iter(ordered_spaces))

    def current_word(self):
        pos = self.position
        word = []

        if self.direction == "across":
            word = [w for w in self.grid.across_words if pos in w][0] 
        if self.direction == "down":
            word = [w for w in self.grid.down_words if pos in w][0]

        return word

    def go_to_numbered_square(self):
        num = int(self.grid.term.inkey(3))
        pos = next(iter([pos for pos in self.grid.cells 
                if self.grid.cells.get(pos).number == num]), None)
        if pos:
            self.position = pos


def main():
    filename = sys.argv[1]
    try:
        puzfile = puz.read(filename)
    except:
        sys.exit("Unable to parse {} as a .puz file.".format(filename))

    term = Terminal()

    grid_x = 2
    grid_y = 2

    grid = Grid(grid_x, grid_y, term)
    grid.load(puzfile)

    if ((term.width < grid_x + 4 * grid.column_count + 2) or
            term.height < grid_y + 2 * grid.row_count + 6):
        exit_text = textwrap.dedent("""\
        This puzzle is {} columns wide and {} rows tall. 
        The current terminal window is too small to 
        properly display it.""".format(
            grid.column_count, grid.row_count))
        sys.exit(''.join(exit_text.splitlines()))

    print(term.enter_fullscreen())
    print(term.clear())

    grid.draw()
    grid.number()
    grid.fill()

    software_info = 'cursewords vX.X'
    puzzle_info = '{grid.title} - {grid.author}'.format(grid=grid)
    padding = 2
    sw_width = len(software_info) + 5
    pz_width = term.width - sw_width - padding
    if len(puzzle_info) > pz_width:
        puzzle_info = "{}…".format(puzzle_info[:pz_width - 1])

    headline = " {:<{pz_w}}{:>{sw_w}} ".format(
            puzzle_info, software_info,
            pz_w=pz_width, sw_w=sw_width)

    with term.location(x=0, y=0):
        print(term.dim(term.reverse(headline)))

    with term.location(x=grid_x, y=term.height):
        toolbar = ''
        commands = [("^Q", "quit"),
                    ("^S", "save"),
                    ("^C", "check puzzle")]
        for shortcut, action in commands:
            shortcut = term.reverse(shortcut)
            toolbar += "{:<25}".format(' '.join([shortcut, action]))
        print(toolbar, end='')

    clue_width = min(int(1.5 * (4 * grid.column_count + 2) - grid_x),
                     term.width - 2 - grid_x)

    clue_wrapper = textwrap.TextWrapper(
            width = clue_width,
            max_lines = 3)

    start_pos = grid.across_words[0][0]
    cursor = Cursor(start_pos, "across", grid)

    old_word = []
    old_position = start_pos
    keypress = ''
    puzzle_complete = False
    to_quit = False

    info_location = {'x':grid_x, 'y':grid_y + 2 * grid.row_count + 2}

    with term.raw(), term.hidden_cursor():
        while not to_quit:

            if cursor.current_word() is not old_word:
                overwrite_mode = False
                for pos in old_word:
                    grid.draw_cell(pos)
                for pos in cursor.current_word():
                    grid.draw_highlighted_cell(pos)

                if cursor.direction == "across":
                    num_index = grid.across_words.index(cursor.current_word())
                    clue = grid.across_clues[num_index]
                elif cursor.direction == "down":
                    num_index = grid.down_words_grouped.index(cursor.current_word())
                    clue = grid.down_clues[num_index]

                num = str(grid.cells.get(cursor.current_word()[0]).number)
                compiled = (num + " " + cursor.direction.upper() \
                                + ": " + clue)
                wrapped_clue = clue_wrapper.wrap(compiled)
                wrapped_clue += [''] * (3 - len(wrapped_clue))
                wrapped_clue = [line + term.clear_eol for line in wrapped_clue]

                for offset in range(0,3):
                    print(term.move(info_location['y'] + offset, info_location['x']) +
                        wrapped_clue[offset], end='')

            else:
                grid.draw_highlighted_cell(old_position)

            current_cell = grid.cells.get(cursor.position)
            value = current_cell.entry
            grid.draw_cursor_cell(cursor.position)

            if not puzzle_complete and all(grid.cells.get(pos).is_correct()
                    for pos in itertools.chain(*grid.across_words)):
                puzzle_complete = True
                with term.location(x=info_location['x'], y=info_location['y']+3):
                    print(term.reverse("You've completed the puzzle!"),
                            term.clear_eol)

            keypress = term.inkey()

            old_position = cursor.position
            old_word = cursor.current_word()

            # ctrl-q
            if keypress == chr(17):
                to_quit = True

            # ctrl-s
            elif keypress == chr(19):
                grid.save(filename)

            # ctrl-c
            elif keypress == chr(3):
                grid.check_puzzle()
                old_word = []

            # ctrl-g
            elif keypress == chr(7):
                cursor.go_to_numbered_square()

            elif not puzzle_complete and keypress in string.ascii_letters:
                if not current_cell.is_blank():
                    overwrite_mode = True
                    # TODO this still doesn't feel quite right
                    # If you type in a few letters towards the end,
                    # you probably expect to proceed to the next word
                    # but I need to figure out the rule
                current_cell.entry = keypress.upper()
                if current_cell.marked_wrong:
                    current_cell.marked_wrong = False
                    current_cell.corrected = True
                cursor.advance_within_word(overwrite_mode)

            elif not puzzle_complete and keypress.name == 'KEY_DELETE':
                current_cell.entry = ' '
                overwrite_mode = True
                if current_cell.marked_wrong:
                    current_cell.marked_wrong = False
                    current_cell.corrected = True
                cursor.retreat_within_word(end_placement=True)

            elif keypress.name in ['KEY_TAB'] and current_cell.is_blank():
                cursor.advance_to_next_word(blank_placement=True)

            elif keypress.name in ['KEY_TAB'] and not current_cell.is_blank():
                cursor.advance_within_word(overwrite_mode=False)

            elif keypress.name in ['KEY_PGDOWN']:
                cursor.advance_to_next_word()

            elif keypress.name in ['KEY_BTAB'] and current_cell.is_blank():
                if cursor.earliest_blank_in_word():
                    cursor.retreat_within_word(blank_placement=True)
                else:
                    cursor.retreat_to_previous_word(blank_placement=True)

            elif keypress.name in ['KEY_BTAB'] and not current_cell.is_blank():
                cursor.retreat_to_previous_word(blank_placement=True)

            elif keypress.name in ['KEY_PGUP']:
                cursor.retreat_to_previous_word()

            elif (keypress.name == 'KEY_ENTER' or keypress == ' ' or
                    (cursor.direction == "across" and
                        keypress.name in ['KEY_DOWN', 'KEY_UP']) or
                    (cursor.direction == "down" and
                        keypress.name in ['KEY_LEFT', 'KEY_RIGHT'])):

                cursor.switch_direction()

            elif ((cursor.direction == "across" and
                        keypress.name == 'KEY_RIGHT') or
                    (cursor.direction == "down" and
                        keypress.name == 'KEY_DOWN')):

                cursor.advance()

            elif ((cursor.direction == "across" and
                        keypress.name == 'KEY_LEFT') or
                    (cursor.direction == "down" and
                        keypress.name == 'KEY_UP')):

                cursor.retreat()

    print(term.exit_fullscreen())

if __name__ == '__main__':
    main()
