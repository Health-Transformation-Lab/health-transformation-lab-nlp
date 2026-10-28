"""Print the end of a Kaggle notebook log: what the cells printed and their errors, without library warnings.

Kaggle's log is a JSON list of {"stream_name", "time", "data"} chunks. Usage: python kaggle/show_log.py LOG [CHARS]
"""

import json
import sys


def main(path, chars=6000):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    try:
        chunks = json.loads(text)
    except json.JSONDecodeError:            # not the JSON form: show it as it is
        print(text[-chars:])
        return
    kept, skip_next = [], False
    for line in "".join(c.get("data", "") for c in chunks).splitlines():
        if skip_next:
            skip_next = False
            continue
        if not line.strip() or line.startswith("[NbConvertApp]"):
            continue
        if "Warning: " in line:             # a Python warning is two lines: the message, then the source line
            skip_next = True
            continue
        kept.append(line)
    print("\n".join(kept)[-chars:])


if __name__ == "__main__":
    main(sys.argv[1], *(int(a) for a in sys.argv[2:3]))
