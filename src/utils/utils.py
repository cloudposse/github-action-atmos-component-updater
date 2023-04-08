import re
from typing import List


def parse_comma_or_new_line_separated_list(items: str) -> List[str]:
    results = []

    if items:
        for item in re.split(',|\n', items):
            item = item.strip()
            if item:
                results.append(item)

    return results
