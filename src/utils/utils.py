import re
from typing import List


def parse_comma_or_new_line_separated_list(items: str) -> List[str]:
    if not items:
        return []

    return [x.strip() for x in re.split(',|\n', items)] if items else []
