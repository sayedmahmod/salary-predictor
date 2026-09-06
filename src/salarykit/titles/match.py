"""Regelbasierte Zuordnung: gesaeuberter Titel -> Taxonomie-Code.

Longest-match auf einem Alias-Gazetteer. Das ist die praezise, aber
unvollstaendige Schicht - alles, was hier durchfaellt, uebernimmt das Modell in
:mod:`salarykit.titles.model`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from salarykit.geo import fold_variants
from salarykit.titles.taxonomy import ROLES_BY_CODE, UNKNOWN, all_aliases

_SEP = re.compile(r"[^0-9a-z&+#]+")


def tokenize(text: str) -> tuple[str, ...]:
    """Vereinheitlichte Tokenfolge fuer den Abgleich.

    Umlaute werden auf beide gaengigen Umschriften gebracht; genommen wird
    die ae/oe/ue-Form, weil die Aliase so hinterlegt sind.
    """
    if not text:
        return ()
    variants = sorted(fold_variants(text), key=len, reverse=True)
    folded = variants[0] if variants else ""
    return tuple(t for t in _SEP.split(folded) if t)


#: Deutsche Flexion am Kopfnomen. "Verkaeufer" steht im Gazetteer, in den
#: Daten steht "Verkaeuferin", "Verkaeufern" oder "Verkaeufers".
def _morph_variants(token: str) -> list[str]:
    if len(token) < 4:
        return [token]
    out = [token, token + "in", token + "innen", token + "n", token + "s",
           token + "e", token + "en"]
    if token.endswith("er"):
        out += [token + "s", token[:-2] + "erin", token[:-2] + "erinnen"]
    if token.endswith("e"):
        out += [token + "r", token + "n", token[:-1]]
    if token.endswith("in") and len(token) > 5:
        out.append(token[:-2])
    return out


#: Endungen, die im Deutschen an das Kopfnomen treten. Wird auf beiden Seiten
#: gleich angewandt, deshalb reicht eine grobe Regel.
_SUFFIXES = ("innen", "inne", "in", "ern", "er", "en", "e", "n", "s")


def lemma(token: str) -> str:
    """Grobe Grundform: Plural-Umlaut zurueck, haeufige Endung ab."""
    if len(token) < 5:
        return token
    stem = token.replace("ae", "a").replace("oe", "o").replace("ue", "u")
    for suffix in _SUFFIXES:
        if stem.endswith(suffix) and len(stem) - len(suffix) >= 4:
            return stem[: -len(suffix)]
    return stem


def lemmatize(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(lemma(t) for t in tokens)


def _build_index() -> tuple[dict[tuple[str, ...], str], int]:
    index: dict[tuple[str, ...], str] = {}
    longest = 1
    exact: list[tuple[tuple[str, ...], str]] = []
    for alias, code in all_aliases():
        key = tokenize(alias)
        if not key:
            continue
        exact.append((key, code))
        index.setdefault(key, code)
        longest = max(longest, len(key))
    # Flexionsformen erst danach, damit sie nie eine exakte Form ueberschreiben
    for key, code in exact:
        head, tail = key[:-1], key[-1]
        for variant in _morph_variants(tail):
            index.setdefault(head + (variant,), code)
    lemma_index: dict[tuple[str, ...], str] = {}
    for key, code in exact:
        lemma_index.setdefault(lemmatize(key), code)
    return index, longest, lemma_index


ALIAS_INDEX, MAX_ALIAS_TOKENS, LEMMA_INDEX = _build_index()


@dataclass(frozen=True)
class RuleMatch:
    code: str
    confidence: float
    matched_alias: str
    span: tuple[int, int]

    @property
    def role(self):
        return ROLES_BY_CODE.get(self.code, UNKNOWN)


def match_title(core: str) -> RuleMatch | None:
    """Laengster Alias gewinnt; bei gleicher Laenge der am weitesten rechts.

    Rechtsbuendig, weil Berufsbezeichnungen im Deutschen wie im Englischen
    ihren Kern am Ende tragen ("Senior Backend Engineer", "Leiter Vertrieb"
    ist die Ausnahme, "Vertriebsleiter" die Regel).
    """
    tokens = tokenize(core)
    if not tokens:
        return None

    result = _scan(tokens, ALIAS_INDEX, tokens, penalty=0.0)
    if result is None:
        # Zweiter Anlauf auf Grundformen - faengt deutsche Flexion und Plural
        # ("Pflegefachkraefte", "Steuerfachangestellte").
        result = _scan(lemmatize(tokens), LEMMA_INDEX, tokens, penalty=0.08)
    return result


def _scan(haystack: tuple[str, ...], index: dict[tuple[str, ...], str],
          original: tuple[str, ...], *, penalty: float) -> RuleMatch | None:
    best: tuple[int, int, str] | None = None
    upper = min(MAX_ALIAS_TOKENS, len(haystack))
    for size in range(upper, 0, -1):
        for start in range(len(haystack) - size + 1):
            code = index.get(haystack[start:start + size])
            if code is None:
                continue
            if best is None or start > best[1]:
                best = (size, start, code)
        if best is not None:          # laengster Treffer gefunden
            break
    if best is None:
        return None
    size, start, code = best
    span = (start, start + size)
    coverage = size / len(haystack)
    confidence = 0.55 + 0.35 * coverage + (0.10 if span[1] == len(haystack) else 0.0)
    if coverage == 1.0:
        confidence = 1.0
    return RuleMatch(code=code, confidence=round(max(min(confidence - penalty, 1.0), 0.0), 3),
                     matched_alias=" ".join(original[start:start + size]), span=span)
