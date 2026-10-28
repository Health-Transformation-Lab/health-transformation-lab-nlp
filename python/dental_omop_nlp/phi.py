"""Fake PHI for synthetic notes.

Real notes carry names, dates, record numbers, phone numbers and places in the
header and inside the text. The synthetic notes carry FAKE ones in the same
places so the de-identification step has something real-shaped to find, and
because we put them there we know exactly where every one is. That makes
de-id recall measurable to the character, which real notes never allow.

Every value here is invented. Names are drawn from common US given/family name
lists; none refers to a real patient.
"""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field

from .telemetry import traced

FIRST = ["James", "Maria", "Robert", "Linda", "Michael", "Patricia", "David", "Jennifer", "Carlos",
         "Aisha", "Wei", "Priya", "Thomas", "Nancy", "Daniel", "Lakisha", "Jose", "Emily", "Kevin",
         "Grace", "Hector", "Fatima", "Brian", "Rosa", "Tyrone", "Mei", "Samuel", "Olga", "Juan", "Ruth"]
LAST = ["Smith", "Johnson", "Garcia", "Nguyen", "Williams", "Brown", "Martinez", "Patel", "Kim",
        "Jones", "Lopez", "Davis", "Hernandez", "Wilson", "Anderson", "Thompson", "Okafor", "Chen",
        "Rivera", "Moore", "Jackson", "Singh", "Clark", "Lewis", "Walker", "Hall", "Young", "King"]
CITIES = ["Tuscaloosa", "Houston", "Springfield", "Riverside", "Fairview", "Madison", "Georgetown",
          "Clinton", "Salem", "Franklin"]
STREETS = ["Oak St", "Maple Ave", "2nd Street", "Elm Dr", "Lakeview Rd", "Pine Ln", "Main Street",
           "Cedar Ct", "Hillcrest Blvd", "Park Ave"]


@dataclass
class Person:
    first: str
    last: str
    dob: dt.date
    mrn: str
    phone: str
    address: str
    city: str


@dataclass
class Provider:
    first: str
    last: str
    practice: str


@traced
def fake_person(rng: random.Random, dob: dt.date) -> Person:
    return Person(rng.choice(FIRST), rng.choice(LAST), dob,
                  f"{rng.randint(10, 99)}{rng.randint(100000, 999999)}",
                  f"({rng.randint(201, 989)}) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
                  f"{rng.randint(10, 9999)} {rng.choice(STREETS)}", rng.choice(CITIES))


@traced
def fake_provider(rng: random.Random) -> Provider:
    last = rng.choice(LAST)
    return Provider(rng.choice(FIRST), last, f"{rng.choice(CITIES)} {rng.choice(['Periodontics', 'Dental Group', 'Family Dentistry'])}")


@dataclass
class Builder:
    """Accumulates note text and records the character span of every PHI value."""
    parts: list[str] = field(default_factory=list)
    spans: list[dict] = field(default_factory=list)
    _len: int = 0

    @traced
    def text(self, s: str) -> Builder:
        self.parts.append(s)
        self._len += len(s)
        return self

    @traced
    def phi(self, s: str, kind: str) -> Builder:
        self.spans.append({"start": self._len, "end": self._len + len(s), "text": s, "type": kind})
        return self.text(s)

    @traced
    def build(self) -> tuple[str, list[dict]]:
        return "".join(self.parts), self.spans


@traced
def fmt_date(d: dt.date, rng: random.Random) -> str:
    return rng.choice([d.strftime("%m/%d/%Y"), d.strftime("%-m/%-d/%y"), d.strftime("%b %d, %Y"),
                       d.isoformat()])
