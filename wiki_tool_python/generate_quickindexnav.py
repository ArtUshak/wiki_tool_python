"""Script to generate {{Quickindexnav}} template for Absurdopedia."""
from typing import Iterator, List

CYRILLIC_LETTERS: List[str] = list('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')


def generate(letters: List[str]) -> Iterator[str]:
    """Get template lines from letters."""
    yield "|'''[{{fullurl:Special:Allpages|from={{{1}}}}} {{{1}}}]:&nbsp;'''"
    first_letter = letters[0]
    last_letter = letters[-1]
    first_letter_u = first_letter.upper()
    last_letter_u = last_letter.upper()
    yield (
        "|[{{fullurl:Special:Allpages|from={{{1}}}}}"
        + first_letter_u + "&to={{{1}}}" + last_letter_u
        + " {{{1}}}" + first_letter_u + "—{{{1}}}" + last_letter_u + "]"
    )
    for i in range(len(letters) - 1):
        letter: str = letters[i]
        next_letter: str = letters[i + 1]
        yield (
            "|[{{fullurl:Special:Allpages|from={{{1}}}}}"
            + letter + "&to={{{1}}}" + next_letter
            + " {{{1}}}" + letter + "]"
        )
    yield (
        "|[{{fullurl:Special:Allpages|from={{{1}}}}}"
        + last_letter + "&to={{{2}}}"
        + " {{{1}}}" + last_letter + "]"
    )
    yield "<noinclude>[[Категория:Шаблоны]]</noinclude>"


if __name__ == "__main__":
    for line in generate(CYRILLIC_LETTERS):
        print(line)
