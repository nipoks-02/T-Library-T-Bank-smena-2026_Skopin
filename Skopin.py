"""
T-Библиотека — персональная консольная система управления книгами.
Автор решения: Скопин Владислав
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


# Цвета терминала

class Clr:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"

def c(text, *styles):
    return "".join(styles) + str(text) + Clr.RESET


# Модель книги

class Book:
    """Единица хранения — книга с метаданными."""

    _counter = 0

    def __init__(self, title: str, author: str, genre: str,
                 year: int, description: str = "",
                 read: bool = False, favourite: bool = False,
                 book_id: int | None = None,
                 added_at: str | None = None):
        if book_id is None:
            Book._counter += 1
            self.id = Book._counter
        else:
            self.id = book_id
            Book._counter = max(Book._counter, book_id)

        self.title       = title.strip()
        self.author      = author.strip()
        self.genre       = genre.strip()
        self.year        = int(year)
        self.description = description.strip()
        self.read        = read
        self.favourite   = favourite
        self.added_at    = added_at or datetime.now().strftime("%Y-%m-%d")

    # Сериализация

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "title":       self.title,
            "author":      self.author,
            "genre":       self.genre,
            "year":        self.year,
            "description": self.description,
            "read":        self.read,
            "favourite":   self.favourite,
            "added_at":    self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Book":
        return cls(
            title=data["title"],
            author=data["author"],
            genre=data["genre"],
            year=data["year"],
            description=data.get("description", ""),
            read=data.get("read", False),
            favourite=data.get("favourite", False),
            book_id=data.get("id"),
            added_at=data.get("added_at"),
        )

    # Отображение

    def status_badge(self) -> str:
        parts = []
        parts.append(c("✓ прочитана", Clr.GREEN) if self.read else c("○ не прочитана", Clr.DIM))
        if self.favourite:
            parts.append(c("★ избранное", Clr.YELLOW))
        return "  ".join(parts)

    def short_line(self) -> str:
        year_str = c(f"({self.year})", Clr.DIM)
        id_str   = c(f"#{self.id}", Clr.CYAN)
        return f"{id_str}  {c(self.title, Clr.BOLD)}  —  {self.author}  {year_str}"

    def full_card(self) -> str:
        w = 56
        sep = c("─" * w, Clr.DIM)
        lines = [
            sep,
            f"  {c('ID:', Clr.DIM)} {c(self.id, Clr.CYAN)}          "
            f"{c('Добавлена:', Clr.DIM)} {self.added_at}",
            f"  {c('Название:', Clr.DIM)} {c(self.title, Clr.BOLD + Clr.WHITE)}",
            f"  {c('Автор:', Clr.DIM)}   {self.author}",
            f"  {c('Жанр:', Clr.DIM)}    {c(self.genre, Clr.MAGENTA)}",
            f"  {c('Год:', Clr.DIM)}     {self.year}",
            f"  {c('Статус:', Clr.DIM)}  {self.status_badge()}",
        ]
        if self.description:
            lines.append(f"  {c('Описание:', Clr.DIM)}")
            # перенос длинного текста
            words, line_buf = self.description.split(), ""
            for w_tok in words:
                if len(line_buf) + len(w_tok) + 1 > 50:
                    lines.append(f"    {line_buf}")
                    line_buf = w_tok
                else:
                    line_buf = (line_buf + " " + w_tok).strip()
            if line_buf:
                lines.append(f"    {line_buf}")
        lines.append(sep)
        return "\n".join(lines)


# Хранилище

class Shelf:
    """Коллекция книг + операции над ней."""

    def __init__(self, filepath: str = "tlib_data.json"):
        self._path  = Path(filepath)
        self._books: list[Book] = []
        self._load()

    # Персистентность

    def _load(self):
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                self._books = [Book.from_dict(d) for d in raw]
                print(c(f"  ✔ Загружено книг: {len(self._books)}", Clr.DIM))
            except (json.JSONDecodeError, KeyError) as exc:
                print(c(f"  ⚠ Ошибка загрузки данных: {exc}", Clr.YELLOW))

    def save(self):
        self._path.write_text(
            json.dumps([b.to_dict() for b in self._books],
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # CRUD

    def add(self, book: Book):
        self._books.append(book)
        self.save()

    def remove(self, book_id: int) -> bool:
        before = len(self._books)
        self._books = [b for b in self._books if b.id != book_id]
        if len(self._books) < before:
            self.save()
            return True
        return False

    def get(self, book_id: int) -> Book | None:
        return next((b for b in self._books if b.id == book_id), None)

    def all_books(self) -> list[Book]:
        return list(self._books)

    # Сортировка

    def filter(self, *,
               genre: str | None = None,
               read: bool | None = None,
               favourite: bool | None = None) -> list[Book]:
        result = self._books
        if genre is not None:
            result = [b for b in result if b.genre.lower() == genre.lower()]
        if read is not None:
            result = [b for b in result if b.read == read]
        if favourite is not None:
            result = [b for b in result if b.favourite == favourite]
        return result

    def sort(self, books: list[Book], key: str = "title") -> list[Book]:
        mapping = {
            "title":  lambda b: b.title.lower(),
            "author": lambda b: b.author.lower(),
            "year":   lambda b: b.year,
            "id":     lambda b: b.id,
        }
        fn = mapping.get(key, mapping["title"])
        return sorted(books, key=fn)

    def search(self, query: str) -> list[Book]:
        q = query.lower()
        return [
            b for b in self._books
            if q in b.title.lower()
            or q in b.author.lower()
            or q in b.description.lower()
        ]

    def genres(self) -> list[str]:
        return sorted({b.genre for b in self._books})


# Утилиты ввода

def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"  {c('›', Clr.CYAN)} {msg}{suffix}: ").strip()
    return value if value else default

def prompt_int(msg: str, default: int | None = None) -> int:
    while True:
        raw = prompt(msg, str(default) if default is not None else "")
        try:
            return int(raw)
        except ValueError:
            print(c("  Введите целое число.", Clr.RED))

def confirm(msg: str) -> bool:
    ans = prompt(f"{msg} (д/н)", "н").lower()
    return ans in ("д", "да", "y", "yes")

def pause():
    input(c("\n  Нажмите Enter для продолжения...", Clr.DIM))

def clear():
    os.system("cls" if os.name == "nt" else "clear")


# Экраны

LOGO = f"""
{c('╔══════════════════════════════════════╗', Clr.BLUE)}
{c('║', Clr.BLUE)}   {c('T - Б И Б Л И О Т Е К А', Clr.BOLD + Clr.WHITE)}            {c('║', Clr.BLUE)}
{c('║', Clr.BLUE)}   {c('Персональный книжный архив', Clr.DIM)}         {c('║', Clr.BLUE)}
{c('╚══════════════════════════════════════╝', Clr.BLUE)}
"""

def print_header(title: str):
    print(f"\n{c('  ═══', Clr.BLUE)} {c(title, Clr.BOLD + Clr.WHITE)} {c('═══', Clr.BLUE)}\n")

def print_books(books: list[Book], empty_msg: str = "Книг не найдено."):
    if not books:
        print(c(f"  {empty_msg}", Clr.DIM))
        return
    for b in books:
        fav = c(" ★", Clr.YELLOW) if b.favourite else "  "
        rd  = c("✓", Clr.GREEN) if b.read else c("○", Clr.DIM)
        print(f"  {rd}{fav}  {b.short_line()}")


# Действия

def action_add(shelf: Shelf):
    print_header("Добавить книгу")
    title  = prompt("Название")
    if not title:
        print(c("  Название обязательно.", Clr.RED))
        return
    author = prompt("Автор")
    genre  = prompt("Жанр")
    year   = prompt_int("Год издания", datetime.now().year)
    desc   = prompt("Краткое описание (необязательно)")
    book = Book(title, author, genre, year, desc)
    shelf.add(book)
    print(c(f"\n  ✔ Книга добавлена с ID #{book.id}", Clr.GREEN))


def action_list(shelf: Shelf):
    print_header("Список книг")

    books = shelf.all_books()
    if not books:
        print(c("  Библиотека пуста.", Clr.DIM))
        return

    # Сортировка
    print(f"  Сортировать по: {c('1', Clr.CYAN)} названию  "
          f"{c('2', Clr.CYAN)} автору  {c('3', Clr.CYAN)} году  "
          f"{c('Enter', Clr.DIM)} без сортировки")
    sort_choice = prompt("Выбор", "0")
    sort_map = {"1": "title", "2": "author", "3": "year"}
    if sort_choice in sort_map:
        books = shelf.sort(books, sort_map[sort_choice])

    # Фильтр по жанру
    genres = shelf.genres()
    if genres:
        print(f"\n  Жанры: {', '.join(c(g, Clr.MAGENTA) for g in genres)}")
        genre_f = prompt("Фильтр по жанру (Enter — все)")
        if genre_f:
            books = [b for b in books if b.genre.lower() == genre_f.lower()]

    # Фильтр по статусу
    print(f"\n  Фильтр статуса: {c('1', Clr.CYAN)} прочитанные  "
          f"{c('2', Clr.CYAN)} непрочитанные  {c('Enter', Clr.DIM)} все")
    status_f = prompt("Выбор", "0")
    if status_f == "1":
        books = [b for b in books if b.read]
    elif status_f == "2":
        books = [b for b in books if not b.read]

    print(f"\n  {c(f'Найдено: {len(books)}', Clr.DIM)}\n")
    print_books(books)


def action_view(shelf: Shelf):
    print_header("Просмотр книги")
    book_id = prompt_int("Введите ID книги")
    book = shelf.get(book_id)
    if not book:
        print(c(f"  Книга #{book_id} не найдена.", Clr.RED))
        return
    print(book.full_card())


def action_toggle_read(shelf: Shelf):
    print_header("Изменить статус прочтения")
    book_id = prompt_int("Введите ID книги")
    book = shelf.get(book_id)
    if not book:
        print(c(f"  Книга #{book_id} не найдена.", Clr.RED))
        return
    book.read = not book.read
    shelf.save()
    state = c("прочитана", Clr.GREEN) if book.read else c("не прочитана", Clr.DIM)
    print(c(f"\n  ✔ «{book.title}» теперь: ", Clr.WHITE) + state)


def action_toggle_fav(shelf: Shelf):
    print_header("Избранное — добавить / убрать")
    book_id = prompt_int("Введите ID книги")
    book = shelf.get(book_id)
    if not book:
        print(c(f"  Книга #{book_id} не найдена.", Clr.RED))
        return
    book.favourite = not book.favourite
    shelf.save()
    state = c("добавлена в избранное ★", Clr.YELLOW) if book.favourite else "убрана из избранного"
    print(c(f"\n  ✔ «{book.title}» — ", Clr.WHITE) + state)


def action_favourites(shelf: Shelf):
    print_header("Избранные книги ★")
    books = shelf.filter(favourite=True)
    print_books(books, "В избранном пусто.")


def action_search(shelf: Shelf):
    print_header("Поиск")
    query = prompt("Ключевые слова")
    if not query:
        return
    results = shelf.search(query)
    print(f"\n  {c(f'Найдено: {len(results)}', Clr.DIM)}\n")
    print_books(results)


def action_delete(shelf: Shelf):
    print_header("Удалить книгу")
    book_id = prompt_int("Введите ID книги")
    book = shelf.get(book_id)
    if not book:
        print(c(f"  Книга #{book_id} не найдена.", Clr.RED))
        return
    print(book.short_line())
    if confirm("  Удалить эту книгу?"):
        shelf.remove(book_id)
        print(c("  ✔ Книга удалена.", Clr.GREEN))
    else:
        print(c("  Отменено.", Clr.DIM))


def action_edit(shelf: Shelf):
    print_header("Редактировать книгу")
    book_id = prompt_int("Введите ID книги")
    book = shelf.get(book_id)
    if not book:
        print(c(f"  Книга #{book_id} не найдена.", Clr.RED))
        return

    print(c("  (Enter — оставить без изменений)", Clr.DIM))
    new_title  = prompt("Название",     book.title)
    new_author = prompt("Автор",        book.author)
    new_genre  = prompt("Жанр",         book.genre)
    new_year   = prompt_int("Год",       book.year)
    new_desc   = prompt("Описание",     book.description)

    book.title       = new_title
    book.author      = new_author
    book.genre       = new_genre
    book.year        = new_year
    book.description = new_desc
    shelf.save()
    print(c("\n  ✔ Изменения сохранены.", Clr.GREEN))


def action_stats(shelf: Shelf):
    print_header("Статистика библиотеки")
    all_b = shelf.all_books()
    if not all_b:
        print(c("  Библиотека пуста.", Clr.DIM))
        return

    total     = len(all_b)
    read_cnt  = sum(1 for b in all_b if b.read)
    fav_cnt   = sum(1 for b in all_b if b.favourite)
    genres    = shelf.genres()

    print(f"  Всего книг:       {c(total, Clr.WHITE + Clr.BOLD)}")
    print(f"  Прочитано:        {c(read_cnt, Clr.GREEN)}  /  {total}")
    print(f"  В избранном:      {c(fav_cnt, Clr.YELLOW)}")
    print(f"  Уникальных жанров:{c(len(genres), Clr.MAGENTA)}")
    if genres:
        print(f"  Жанры: {', '.join(genres)}")

    if all_b:
        years = [b.year for b in all_b]
        print(f"  Годы изданий:     {min(years)} – {max(years)}")


# Главное меню

MENU = [
    ("1", "Добавить книгу",              action_add),
    ("2", "Список всех книг",            action_list),
    ("3", "Просмотр карточки книги",     action_view),
    ("4", "Изменить статус прочтения",   action_toggle_read),
    ("5", "Избранное ★  (добавить/убрать)", action_toggle_fav),
    ("6", "Список избранных книг",       action_favourites),
    ("7", "Поиск",                       action_search),
    ("8", "Редактировать книгу",         action_edit),
    ("9", "Удалить книгу",               action_delete),
    ("0", "Статистика",                  action_stats),
    ("q", "Выход",                       None),
]

def show_menu():
    print()
    for key, label, _ in MENU:
        key_str = c(f" {key} ", Clr.BOLD + Clr.BLUE)
        print(f"  {key_str}  {label}")
    print()


def run():
    clear()
    print(LOGO)

    shelf = Shelf()

    while True:
        show_menu()
        choice = prompt("Выберите действие").lower()

        handler = None
        for key, _, fn in MENU:
            if choice == key:
                handler = fn
                break

        if handler is None and choice != "q":
            print(c("  Неверный выбор.", Clr.RED))
            continue

        if choice == "q":
            print(c("\n  До свидания! Книги сохранены.\n", Clr.DIM))
            shelf.save()
            sys.exit(0)

        clear()
        try:
            handler(shelf)
        except KeyboardInterrupt:
            print(c("\n  Прервано.", Clr.DIM))
        pause()
        clear()
        print(LOGO)


if __name__ == "__main__":
    run()