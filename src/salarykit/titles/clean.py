"""Jobtitel saeubern und Attribute herausloesen.

Ein Rohtitel aus einer Stellenboerse enthaelt typischerweise weit mehr als den
Beruf::

    "Senior Data Scientist (m/w/d) - Muenchen | Vollzeit, Remote (Req #12345)"

Der Cleaner zerlegt das in:

* ``core``               -> "Data Scientist"   (Input fuer den Klassifikator)
* ``clean``              -> "Senior Data Scientist"
* ``seniority``          -> "senior"
* ``place``              -> Muenchen / Bayern / DE
* ``employment_type``    -> "full_time"
* ``remote_type``        -> "remote"

Reihenfolge der Schritte ist relevant: erst Unicode/Muell, dann Gendering
(sonst zerschiesst "/in" die Tokenisierung), dann Vertrag/Arbeitsmodell,
dann Seniority, zuletzt der Ort (der am ehesten Fehlalarme produziert).
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field

from salarykit.geo import (COUNTRY_NAMES, MAX_PLACE_TOKENS, PLACE_LOOKUP, Place,
                           US_STATES, fold_variants, lookup_place)

# --------------------------------------------------------------------------
# 0 - Unicode / Zeichenmuell
# --------------------------------------------------------------------------

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"',
           ord("”"): '"', ord("´"): "'", ord("`"): "'"}
_SLASHES = {ord("⁄"): "/", ord("／"): "/"}
_TRANSLATE = {**_DASHES, **_QUOTES, **_SLASHES}

_EMOJI = re.compile(
    "[" "\U0001f000-\U0001faff" "\U00002190-\U000021ff" "\U00002300-\U000023ff"
    "\U00002460-\U000024ff" "\U000025a0-\U000027bf" "\U00002b00-\U00002bff"
    "\U0000fe00-\U0000fe0f" "\U0001f1e6-\U0001f1ff" "★☆✔✱❌"
    "]+"
)
_CTRL = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮﻿]")


def _normalize_unicode(text: str) -> str:
    text = html.unescape(str(text))
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_TRANSLATE)
    text = _EMOJI.sub(" ", text)
    text = _CTRL.sub(" ", text)
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# 1 - Requisition-IDs, Codes, Adressen
# --------------------------------------------------------------------------

_REQ_PATTERNS = [
    re.compile(r"\(\s*#?\s*\d{3,}\s*\)"),                       # (03263)
    re.compile(r"\[\s*#?\s*\d{3,}\s*\]"),
    re.compile(r"(?i)\b(?:req(?:uisition)?|job|stellen|position|vacancy|ref(?:erenz)?)"
               r"[\s.:#_-]*(?:id|nr\.?|no\.?|nummer|code)?[\s.:#_-]*\d{3,}\b"),
    re.compile(r"(?i)\b(?:id|ref)[\s.:#_-]*\d{4,}\b"),
    re.compile(r"#\s?\d{3,}"),
    re.compile(r"(?i)\bkennziffer[\s.:#_-]*[\w-]+"),
    # Strassenadressen am Ende: "- 3171 W. Vine Street", "- 12600 Fm 1764 Rd"
    re.compile(r"(?i)[-–|,]\s*\d{2,6}\s+[\w.\s]{2,30}\b"
               r"(?:st|street|str|rd|road|ave|avenue|blvd|boulevard|dr|drive|"
               r"ln|lane|hwy|highway|pkwy|fm|way|ct|court|pl|place)\b\.?.*$"),
]


def _strip_req_ids(text: str) -> str:
    for pat in _REQ_PATTERNS:
        text = pat.sub(" ", text)
    return text


# --------------------------------------------------------------------------
# 2 - Gendering
# --------------------------------------------------------------------------

# Buchstaben, die in Geschlechtskuerzeln vorkommen (de/en/fr/it/nl/pl/sl/cz)
_G = r"(?:divers[e]?|div\.?|dv|gn|all|any|m|w|f|d|h|x|a|n|v|k|z|ž|i)"
_GENDER_TOKEN = re.compile(
    rf"(?<![\w])[\(\[]?\s*{_G}\s*(?:[/|·:]\s*{_G}\s*){{1,3}}\)?\]?\.?(?![\w])",
    re.IGNORECASE,
)
# Mindestens ein "echter" Geschlechtsbuchstabe muss dabei sein, sonst ist es
# eher "A/B Testing" o.ae.
_GENDER_REQUIRED = re.compile(r"(?i)(?<![a-z])(?:m|w|f|d|h|x|gn|div)(?![a-z])")

_GENDER_PHRASES = re.compile(
    r"(?i)\(?\s*(?:all\s+genders?(?:\s+welcome)?|any\s+gender|alle\s+geschlechter|"
    r"geschlechtsneutral|gender\s*neutral)\s*\)?"
)

# Doppelnennungen / inklusive Endungen
_GENDER_SUFFIX_RULES = [
    # Mitarbeiter/in, Mitarbeiter/-in, Mitarbeiter/innen
    (re.compile(r"(?i)\b([a-zäöüß]{3,})/\-?(?:in|innen|r|e|frau|mann)\b"), r"\1"),
    # Mitarbeiter*innen, Mitarbeiter:innen, Mitarbeiter_innen
    (re.compile(r"(?i)\b([a-zäöüß]{3,})[*:_]in(?:nen)?\b"), r"\1"),
    # Binnen-I: MitarbeiterInnen
    (re.compile(r"\b([A-ZÄÖÜ][a-zäöüß]{2,})In(?:nen)?\b"), r"\1"),
    # Mitarbeiter(in), Ingenieur(e), Technicien(ne), Consultant(e), Chargé(e)
    (re.compile(r"(?i)\b([a-zäöüßéèêàçñ]{3,})\((?:in|innen|e|r|n|ne|se|le|re|ère|"
                r"euse|trice|rice|a|es)\)"), r"\1"),
    # Addetto/a, Impiegato/a, Operaio/a  (it/es)
    (re.compile(r"(?i)\b([a-zàèéìòù]{3,})/a\b"), r"\1"),
    # Demi-chef·fe, employé·e
    (re.compile(r"(?i)\b([a-zäöüßéèêàç]{3,})·[a-zäöüßéèêàç]{1,4}\b"), r"\1"),
    # Verkäufer / Verkäuferin  (ausgeschriebene Doppelnennung)
    (re.compile(r"(?i)\b([a-zäöüß]{4,})\s*/\s*\1(?:in|innen|e|a)\b"), r"\1"),
]


def _strip_gender(text: str) -> tuple[str, bool]:
    hit = False
    new = _GENDER_PHRASES.sub(" ", text)
    hit |= new != text
    text = new

    def _repl(m: re.Match) -> str:
        nonlocal hit
        token = m.group(0)
        if not _GENDER_REQUIRED.search(token):
            return token
        # "Front/Backend" schuetzen: mehrbuchstabige Teile sind kein Gendering
        parts = re.split(r"[/|·:]", token.strip(" ()[].").strip())
        if any(len(p.strip(" ().")) > 3 for p in parts):
            return token
        hit = True
        return " "

    text = _GENDER_TOKEN.sub(_repl, text)
    for pat, repl in _GENDER_SUFFIX_RULES:
        new = pat.sub(repl, text)
        hit |= new != text
        text = new
    return text, hit


# --------------------------------------------------------------------------
# 3 - Vertragsart / Arbeitszeit
# --------------------------------------------------------------------------

_EMPLOYMENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("working_student", re.compile(
        r"(?i)\b(?:werkstudent(?:in|en)?|working\s+student|praxisstudent(?:in)?|"
        r"studentische[rn]?\s+(?:hilfskraft|aushilfe)|wissenschaftliche\s+hilfskraft)\b")),
    ("apprenticeship", re.compile(
        r"(?i)\b(?:ausbildung(?:splatz)?|azubi|auszubildende[rn]?|apprentice(?:ship)?|"
        r"lehrling|lehrstelle|duales?\s+studium|dual\s+study)\b")),
    ("internship", re.compile(
        r"(?i)\b(?:internship|\w*praktikum|praktikant(?:in|en)?|"
        r"stagiaire|tirocinio|becario|pasant[ií]a)\b")),
    ("freelance", re.compile(
        r"(?i)\b(?:freelance[rd]?|freiberuflich|self[- ]employed|selbst[aä]ndig|"
        r"independent\s+contractor|fractional|honorarbasis)\b")),
    ("temporary", re.compile(
        r"(?i)\b(?:temporary|tempor[aä]r|befristet|fixed[- ]term|ftc|interim|"
        r"int[eé]rim|cdd|seasonal|saison(?:al)?|casual|per\s+diem|aushilfe|"
        r"zeitarbeit|leiharbeit|\d{1,2}\s*[- ]?\s*month(?:s)?\s*(?:contract|ftc|fixed))\b")),
    ("contract", re.compile(r"(?i)\b(?:contract(?:or)?|vertragsbasis|w2|c2c)\b")),
    ("part_time", re.compile(
        r"(?i)\b(?:part[- ]?time|teilzeit|temps\s+partiel|tempo\s+parziale|"
        r"media\s+jornada|minijob|geringf[uü]gig(?:e|ig)?|deeltijd|"
        r"\d{1,2}\s*(?:h|std\.?|hrs?|hours?|stunden)\s*(?:/|\s+pro\s+|\s+per\s+)"
        r"\s*(?:woche|week|wk|wo\.?)|\d{1,2}\s*h\s*/\s*w(?:oche)?)\b")),
    ("full_time", re.compile(
        r"(?i)\b(?:full[- ]?time|vollzeit|temps\s+plein|tempo\s+pieno|"
        r"jornada\s+completa|voltijd|unbefristet|permanent|festanstellung|cdi)\b")),
]
# "Voll-/Teilzeit", "Vollzeit oder Teilzeit" -> keine eindeutige Zuordnung
_BOTH_TIMES = re.compile(r"(?i)\bvoll\s*[-/]\s*(?:und\s+|oder\s+)?teilzeit\b|"
                         r"\bvollzeit\s+(?:und|oder|/)\s+teilzeit\b|"
                         r"\bfull[- ]?\s*/\s*part[- ]?time\b")
_HOURS = re.compile(r"(?i)\b\d{1,2}\s*(?:[-–]\s*\d{1,2}\s*)?"
                    r"(?:h|std\.?|hrs?|hours?|stunden)\s*(?:/|\s+pro\s+|\s+per\s+)?"
                    r"\s*(?:woche|week|wk|wo\.?|w)\b")


def _strip_employment(text: str) -> tuple[str, str | None]:
    found: str | None = None
    if _BOTH_TIMES.search(text):
        text = _BOTH_TIMES.sub(" ", text)
    text = _HOURS.sub(" ", text)
    for label, pat in _EMPLOYMENT_PATTERNS:
        if pat.search(text):
            if found is None:
                found = label
            # Praktikum/Werkstudent bleiben als Seniority-Signal erhalten und
            # werden erst nach der Seniority-Erkennung entfernt.
            if label in {"internship", "working_student", "apprenticeship"}:
                continue
            text = pat.sub(" ", text)
    return text, found


# --------------------------------------------------------------------------
# 4 - Arbeitsmodell
# --------------------------------------------------------------------------

_REMOTE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("hybrid", re.compile(r"(?i)\bhybrid(?:es\s+arbeiten)?\b")),
    ("remote", re.compile(
        r"(?i)\b(?:\d{1,3}\s*%\s*)?(?:fully\s+|full\s+|voll\s+)?remote"
        r"(?:[- ]?(?:first|friendly|only|eu|us|emea|europe|germany|de|worldwide|global))?\b"
        r"|\bhome\s?office\b|\bhomeoffice\b|\bwfh\b|\btelearbeit\b|"
        r"\bmobiles\s+arbeiten\b|\bortsunabh[aä]ngig\b|\bwork\s+from\s+home\b")),
    ("onsite", re.compile(r"(?i)\bon[- ]?site\b|\bvor\s+ort\b|\bpr[aä]senz\b|\bin[- ]person\b")),
]


def _strip_remote(text: str) -> tuple[str, str | None]:
    found = None
    for label, pat in _REMOTE_PATTERNS:
        if pat.search(text):
            found = found or label
            text = pat.sub(" ", text)
    return text, found


# --------------------------------------------------------------------------
# 5 - Sprachanforderungen, Gehalt, Marketing
# --------------------------------------------------------------------------

_LANGS = (r"german|deutsch|english|englisch|french|franz[oö]sisch|spanish|spanisch|"
          r"italian|italienisch|dutch|niederl[aä]ndisch|polish|polnisch|portuguese|"
          r"portugiesisch|swedish|schwedisch|danish|d[aä]nisch|norwegian|norwegisch|"
          r"finnish|finnisch|czech|tschechisch|romanian|rum[aä]nisch|hungarian|"
          r"ungarisch|greek|griechisch|turkish|t[uü]rkisch|arabic|arabisch|mandarin|"
          r"chinese|chinesisch|japanese|japanisch|korean|koreanisch|russian|russisch|"
          r"ukrainian|ukrainisch|vietnamese|vietnamesisch|indonesian|indonesisch|"
          r"hindi|hebrew|hebr[aä]isch|flemish|fl[aä]misch|slovak|slowakisch|"
          r"slovenian|slowenisch|croatian|kroatisch|bulgarian|bulgarisch")
_LANG_PATTERNS = [
    re.compile(rf"(?i)\(\s*(?:w/|with|mit|in)?\s*({_LANGS})\s*\)"),
    re.compile(rf"(?i)\b({_LANGS})[- ]?(?:speaking|speaker|language|sprachig|"
               r"sprechend|kenntnisse|native)\b"),
    re.compile(rf"(?i)\b(?:native|fluent|verhandlungssicher(?:es)?|flie[sß]end(?:es)?)\s+"
               rf"({_LANGS})\b"),
    re.compile(rf"(?i)\b(?:w/|with|mit)\s+({_LANGS})(?:kenntnissen)?\b"),
    re.compile(rf"(?i)\b({_LANGS})kenntnisse\w*\b"),
    # haengende Aufzaehlung: "Vietnamesisch- & Deutschsprachig"
    re.compile(rf"(?i)\b({_LANGS})\s*-\s*(?=&|und\b|and\b|,)"),
]

_SALARY_IN_TITLE = re.compile(
    r"(?i)(?:up\s+to\s+|bis\s+(?:zu\s+)?|ab\s+|from\s+)?"
    r"(?:[€£$]|eur|gbp|usd|chf)\s?\d[\d.,]*\s*(?:k|000|tsd)?"
    r"(?:\s*[-–]\s*(?:[€£$]|eur|gbp|usd|chf)?\s?\d[\d.,]*\s*(?:k|000|tsd)?)?"
    r"(?:\s*(?:p\.?a\.?|per\s+year|pro\s+jahr|/\s*(?:jahr|year|h|hr|hour|std)))?"
)
_SALARY_AMOUNT = re.compile(
    r"(?i)\(?\s*(?:up\s+to\s+|bis\s+(?:zu\s+)?|ab\s+)?\d[\d.,']*\s*"
    r"(?:k|tsd)?\s*(?:eur|usd|gbp|chf|pln|czk|huf|ron|sek|nok|dkk|brutto|netto)"
    r"(?:\s*(?:/|pro\s+|per\s+)\s*(?:monat|month|jahr|year|h|std))?\s*\)?")
_SALARY_WORDS = re.compile(r"(?i)\b(?:gehalt|salary|verg[uü]tung|attraktive[sr]?\s+gehalt|"
                           r"bonus|sign[- ]on)\b[^,|\-–]*")

_MARKETING = re.compile(
    r"(?i)\b(?:neu|new|urgent|dringend|sofort|ab\s+sofort|immediate\s+start|"
    r"we\s+are\s+hiring|now\s+hiring|hiring|apply\s+now|jetzt\s+bewerben|"
    r"top[- ]job|traumjob|deine\s+chance|gesucht|wanted|m/w/d|join\s+us|"
    r"quereinsteiger\s+willkommen|willkommen)\b"
)
_OPEN_APPLICATION = re.compile(
    r"(?i)\b(?:initiativbewerbung|general\s+application|speculative\s+application|"
    r"talent\s*pool|talent\s+community|open\s+application|candidature\s+spontan[eé]e|"
    r"future\s+opportunities|test\s+w[yz]?\d+)\b"
)


def _strip_language(text: str) -> tuple[str, list[str]]:
    langs: list[str] = []
    for pat in _LANG_PATTERNS:
        for m in pat.finditer(text):
            langs.append(m.group(1).lower())
        text = pat.sub(" ", text)
    return text, sorted(set(langs))


def _strip_noise(text: str) -> str:
    text = _SALARY_IN_TITLE.sub(" ", text)
    text = _SALARY_AMOUNT.sub(" ", text)
    text = _SALARY_WORDS.sub(" ", text)
    text = _MARKETING.sub(" ", text)
    return text


# --------------------------------------------------------------------------
# 6 - Seniority
# --------------------------------------------------------------------------

#: Rollen, in denen "Staff" das Nomen ist und keine Karrierestufe: entweder
#: Personal selbst oder eine Rolle, die Personal fuehrt bzw. betreut.
_STAFF_ROLE_NOUNS = (
    r"nurses?|accountants?|consultants?|attorneys?|physicians?|pharmacists?|"
    r"writers?|auditors?|assistants?|therapists?|recruiters?|editors?|"
    r"officers?|managers?|supervisors?|coordinators?|schedulers?|"
    r"augmentation|sergeants?|chaplains?|dentists?|psychologists?|"
    r"veterinarians?|members?|to"
)

_SENIORITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("executive", re.compile(
        r"(?i)\b(?:c[eoftisdmrp]o|cxo|chief\s+[\w\s]{0,20}?officer|"
        r"gesch[aä]ftsf[uü]hr(?:er|ung|erin)|vorstand(?:svorsitzende[rn]?)?|"
        r"managing\s+director|general\s+manager|president|"
        r"(?:s|e)?vp|vice\s+president|inhaber|owner|"
        r"founder|gr[uü]nder|co[- ]?founder|partner)\b")),
    ("director", re.compile(
        r"(?i)\b(?:director|direktor(?:in)?|bereichsleit(?:er|erin|ung)|"
        r"abteilungsleit(?:er|erin|ung)|werkleit(?:er|ung))\b")),
    ("head", re.compile(
        r"(?i)\bhead\s+(?:of|de|:)|\bhead,|^head\b|\bleiter(?:in)?\b|\bleitung\b|"
        r"\b\w+leiter(?:in)?\b|\b\w+leitung\b|\bressortleit\w+\b|\bstandortleit\w+\b")),
    ("lead", re.compile(
        r"(?i)\b(?:lead|leads|team\s?lead(?:er)?|tech\s?lead|squad\s+lead|"
        r"teamleit(?:er|erin|ung)|gruppenleit(?:er|erin|ung)|"
        r"schichtleit(?:er|erin|ung)|projektleit(?:er|erin|ung)|"
        r"supervisor|vorarbeiter|meister)\b")),
    ("principal", re.compile(r"(?i)\bprincipal\b|\bchef(?:in)?ingenieur\b")),
    # "Staff" ist nur dann eine Stufe, wenn es einer Rolle vorangestellt ist.
    # Eine Whitelist der Folgewoerter reicht nicht: die Tech-Vokabeln dahinter
    # sind ein offener Long Tail (analog, propulsion, fpga, gnc, cobol ...).
    # Darum umgekehrt - alles ausser den Faellen, in denen "Staff" das Nomen
    # selbst ist: am Wortende ("member of technical staff", "support staff"),
    # nach "of" oder vor einer der Rollen, die Personal bezeichnen oder
    # fuehren ("staff nurse", "staff accountant", "staff supervisor").
    ("staff", re.compile(
        r"(?i)(?<!\bof\s)\bstaff\s+(?!" + _STAFF_ROLE_NOUNS + r"\b)(?=[a-z0-9])")),
    ("senior", re.compile(
        r"(?i)\b(?:senior|sr\.?|snr|leitende[rn]?|erfahrene[rn]?|experienced|"
        r"experte?[nr]?|expert|exp[eé]riment[eé]e?|seniore?)\b")),
    ("mid", re.compile(r"(?i)\bmid[- ]?(?:level|senior)?\b|\bintermediate\b|"
                       r"\bregular\b|\b(?:II|III)\b|\b(?:l|level|lvl)\s?[34]\b")),
    ("junior", re.compile(r"(?i)\bjunior\b|\bjr\.?\b|\bjun\.\b|\bjunior[- ]?level\b")),
    ("entry", re.compile(
        r"(?i)\b(?:entry[- ]?level|graduate|new\s+grad|absolvent(?:in|en)?|"
        r"berufseinsteiger(?:in)?|einsteiger|nachwuchs\w*|trainee|"
        r"associate|junior\s+associate|d[eé]butant(?:e)?|"
        r"quereinsteiger(?:in)?|anf[aä]nger)\b")),
    ("intern", re.compile(
        r"(?i)\b(?:intern|internship|praktikant(?:in|en)?|\w*praktikum|"
        r"werkstudent(?:in|en)?|working\s+student|praxisstudent(?:in)?|"
        r"stagiaire|azubi|auszubildende[rn]?|ausbildung|apprentice\w*|"
        r"lehrling|duales?\s+studium|student\s+(?:worker|assistant)|"
        r"studentische[rn]?\s+(?:hilfskraft|aushilfe))\b")),
]
_SENIORITY_ORDER = {name: i for i, (name, _) in enumerate(_SENIORITY_PATTERNS)}

# Diese Rollen heissen so, auch wenn ein Seniority-Wort drinsteckt - hier darf
# das Wort nicht aus dem Kern entfernt werden, sonst bleibt nichts uebrig.
_ROLE_IS_SENIORITY = re.compile(
    r"(?i)^(?:chief\s+of\s+staff|founder(?:s)?\s+associate\w*|"
    r"(?:sales|account|customer|hr|talent|office|product|project|program|"
    r"engineering|marketing|finance|store|general|assistant|branch|"
    r"restaurant|operations|construction|category|community|content|"
    r"partner|portfolio|brand|regional|district|country|delivery)?\s*"
    r"(?:manager|managerin|director|lead|leiter|leitung|supervisor|"
    r"executive|associate|partner|president|meister|vorarbeiter)s?)$"
)


#: Woerter, die zwar eine Stufe anzeigen, aber zugleich die Rolle *bilden*
#: ("Art Director", "ROV Supervisor"). Sie fliegen nur raus, wenn danach noch
#: ein brauchbarer Kern uebrig bleibt.
_ROLE_FORMING_WORDS = {
    "director", "direktor", "directorin", "head", "lead", "leads", "leiter",
    "leiterin", "leitung", "associate", "partner", "owner", "inhaber",
    "supervisor", "meister", "vorarbeiter", "president", "executive",
    "principal", "manager", "chief of staff", "founder", "gruender",
}
_USABLE_CORE = re.compile(r"[A-Za-zÄÖÜäöüßÉÈÊÀÇÑ]{3,}")


def _usable(text: str) -> bool:
    """Bleibt nach dem Kuerzen noch ein sinnvoller Titel uebrig?"""
    text = _clean_ws(text)
    if not _USABLE_CORE.search(text):
        return False
    tokens = [t for t in re.split(r"[\s/&,\-]+", text) if t]
    if len(tokens) == 1 and len(re.sub(r"[^A-Za-zÄÖÜäöüß]", "", tokens[0])) < 7:
        return False
    return True


def _strip_levels(text: str, hits: list[str], *, keep_role_forming: bool) -> str:
    def _sub(match: re.Match) -> str:
        if keep_role_forming and match.group(0).strip().lower() in _ROLE_FORMING_WORDS:
            return match.group(0)
        return " "

    for name, pat in _SENIORITY_PATTERNS:
        if name not in hits:
            continue
        candidate = pat.sub(_sub, text)
        if _USABLE_CORE.search(candidate):
            text = candidate
    return _clean_ws(text)


def _extract_seniority(text: str) -> tuple[str, str | None, list[str]]:
    """Hoechste gefundene Stufe gewinnt (Senior Director -> director).

    Zurueck kommt der Titel *ohne* Stufenwoerter. Wuerde dabei nichts
    Brauchbares uebrig bleiben, werden rollenbildende Woerter wieder
    stehen gelassen.
    """
    hits = [name for name, pat in _SENIORITY_PATTERNS if pat.search(text)]
    if not hits:
        return text, None, []
    level = min(hits, key=lambda n: _SENIORITY_ORDER[n])

    stripped = _strip_levels(text, hits, keep_role_forming=False)
    if not _usable(stripped):
        stripped = _strip_levels(text, hits, keep_role_forming=True)
    if not _USABLE_CORE.search(stripped):
        stripped = text
    return stripped, level, hits


# --------------------------------------------------------------------------
# 7 - Ort
# --------------------------------------------------------------------------

# Ortsnamen, die im Englischen/Deutschen auch ganz normale Woerter sind. Sie
# zaehlen nur in eindeutigem Kontext (Klammer, eigenes Segment, Praeposition),
# nie als blosser Titel-Suffix.
_AMBIGUOUS_PLACES = {
    "essen", "halle", "zug", "worms", "nice", "reading", "mobile", "island",
    "georgia", "jordan", "chad", "bern", "hof", "delft", "bergen", "victoria",
    "phoenix", "jersey", "china", "turkey", "chile", "florence", "sydney",
    "austin", "dallas", "orange", "mainz", "kiel", "bonn", "celle", "hagen",
    "us", "uk", "eu", "de", "at", "ch", "it", "in", "no", "so", "an", "am",
    "global", "europe", "europa", "brooklyn", "cork", "split", "most",
}
_LOC_PREPOSITION = re.compile(
    r"(?i)\b(?:in|bei|im\s+raum|raum|region|standort|location|based\s+in|"
    r"[aà]|au|sede\s+di|w|na)\s*:?\s*$"
)
# Trenner: Pipe, Semikolon, Komma, Aufzaehlungszeichen und Bindestriche, an
# denen mindestens auf einer Seite ein Leerzeichen steht (damit "Full-Stack"
# heil bleibt).
_SEGMENT_SPLIT = re.compile(r"\s*(?:\||;|·|•|,|\s[-–]\s|(?<=\S)[-–]\s|\s[-–](?=\S))\s*")
_PAREN = re.compile(r"[\(\[]([^)\]]*)[\)\]]")


# Woerter, die einen Berufsbezug signalisieren. Ein Segment, das so ein Wort
# enthaelt, wird nie als reines Ortssegment weggeworfen.
_ROLE_HINT = re.compile(
    r"(?i)\b(?:engineer|developer|entwickl\w+|manager|managerin|analyst|scientist|"
    r"architekt\w*|architect|designer|consultant|berater\w*|specialist|spezialist\w*|"
    r"assistant|assistenz|administrator|technician|techniker\w*|nurse|pflege\w*|"
    r"sales|vertrieb|marketing|support|service|operations|finance|legal|"
    r"recruit\w+|teacher|lehrer\w*|driver|fahrer\w*|chef|koch|cook|clerk|"
    r"officer|director|lead|leiter\w*|head|intern|praktikant\w*|research\w*|"
    r"produkt|product|project|projekt|program|data|software|security|cloud|"
    r"mitarbeiter\w*|fachkraft|helfer\w*|kaufmann|kauffrau|monteur|mechanik\w*)\b"
)
_DIGIT = re.compile(r"\d")


def _place_pieces(segment: str) -> list[str]:
    seg = segment.strip(" .-/&")
    if not seg or len(seg) > 60:
        return []
    pieces = [p.strip() for p in re.split(r"\s*[,/&]\s*|\s+und\s+|\s+and\s+|\s+oder\s+", seg)
              if p.strip()]
    return pieces if 1 <= len(pieces) <= 4 else []


_OFFICE_NOISE = re.compile(
    r"(?i)\b(?:hq|headquarters?|office|b[uü]ro|area|region|metro|downtown|"
    r"campus|site|standort|store|mall|city|centre|center|zentrale|werk|"
    r"greater|gro[sß]raum|umgebung|nord|s[uü]d|ost|west|north|south|east)\b")


def _resolve_one(piece: str) -> Place | None:
    piece = piece.strip()
    place = lookup_place(piece)
    if place is not None:
        return place
    # US-Bundesstaat als Kuerzel ("Cambridge, MA")
    if len(piece) == 2 and piece.isupper() and piece in US_STATES:
        return Place(country_iso2="US", country_name=COUNTRY_NAMES["US"],
                     region=US_STATES[piece])
    # Buero-Fuellwoerter weg ("San Francisco HQ", "Greater London")
    trimmed = _clean_ws(_OFFICE_NOISE.sub(" ", piece))
    if trimmed and trimmed != piece:
        place = lookup_place(trimmed)
        if place is not None:
            return place
    # Stadtteil am Bindestrich ("Berlin-Pankow", "Frankfurt-Hoechst")
    if "-" in piece:
        head = piece.split("-", 1)[0].strip()
        if len(head) > 2:
            place = lookup_place(head)
            if place is not None:
                return place
    # "East Texas", "Greater London", "Muenchen Ost", "London UK"
    words = piece.split()
    if 2 <= len(words) <= 3:
        for sub in (" ".join(words[-2:]), words[-1], words[0]):
            place = lookup_place(sub)
            if place is not None:
                return place
    return None


def _resolve_segment(segment: str, *, strict: bool = True) -> Place | None:
    """Ein Segment als Ort aufloesen.

    ``strict``  - jedes Teilstueck muss ein Ort sein ("Muenchen, Bayern").
    sonst       - ein Treffer reicht, solange kein Teil nach Beruf klingt
                  ("Cross Timbers, East Texas").
    """
    pieces = _place_pieces(segment)
    if not pieces:
        return None
    if not strict and (_ROLE_HINT.search(segment) or _DIGIT.search(segment)):
        return None
    resolved: list[Place] = []
    for piece in pieces:
        place = _resolve_one(piece)
        if place is None:
            if strict:
                return None
            continue
        resolved.append(place)
    if not resolved:
        return None
    return _merge_places(resolved)


def _merge_places(places: list[Place]) -> Place | None:
    city = region = iso = name = None
    for p in places:
        city = city or p.city
        region = region or p.region
        if iso is None:
            iso, name = p.country_iso2, p.country_name
    if city is None and region is None and iso is None:
        return None
    return Place(country_iso2=iso, country_name=name, region=region, city=city)


def _cut_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Zeichenbereiche entfernen, ohne die uebrigen Trenner zu verwuerfeln."""
    if not spans:
        return text
    out, prev = [], 0
    for a, b in sorted(spans):
        if a < prev:
            continue
        out.append(text[prev:a])
        prev = b
    out.append(text[prev:])
    return "".join(out)


def _extract_location(text: str) -> tuple[str, Place | None]:
    place: Place | None = None
    spans: list[tuple[int, int]] = []

    # a) Klammerinhalte, die (auch nur teilweise) ein Ort sind
    for m in _PAREN.finditer(text):
        hit = _resolve_segment(m.group(1), strict=False)
        if hit is not None:
            place = place or hit
            spans.append(m.span())
    text = _clean_ws(_cut_spans(text, spans))

    # b) Segmente nach einem Trenner, die komplett ein Ort sind. Das erste
    #    Segment ist immer der Beruf und wird nie angefasst.
    spans = []
    seps = [m for m in _SEGMENT_SPLIT.finditer(text)]
    if seps:
        bounds = []
        for i, m in enumerate(seps):
            seg_start = m.end()
            seg_end = seps[i + 1].start() if i + 1 < len(seps) else len(text)
            bounds.append((m.start(), seg_start, seg_end))
        for sep_start, seg_start, seg_end in bounds:
            segment = text[seg_start:seg_end]
            hit = _resolve_segment(segment, strict=False)
            if hit is not None:
                place = place or hit
                spans.append((sep_start, seg_end))
        text = _clean_ws(_cut_spans(text, spans))

    # c) Praeposition + Ort ("... in Berlin", "... Raum Stuttgart") oder ein
    #    eindeutiger Ort ganz am Ende ("Data Scientist Berlin").
    tokens = text.split()
    for size in range(min(MAX_PLACE_TOKENS, len(tokens)), 0, -1):
        for begin in range(len(tokens) - size + 1):
            candidate = " ".join(tokens[begin:begin + size]).strip(" .,()")
            if not any(v in PLACE_LOOKUP for v in fold_variants(candidate)):
                continue
            before = " ".join(tokens[:begin])
            is_suffix = begin + size == len(tokens)
            prep = _LOC_PREPOSITION.search(before)
            ambiguous = any(v in _AMBIGUOUS_PLACES for v in fold_variants(candidate))
            if not (prep or (is_suffix and not ambiguous)):
                continue
            head = before[:prep.start()] if prep else before
            if not _clean_ws(head):          # sonst bliebe kein Titel uebrig
                continue
            hit = _resolve_one(candidate)
            if hit is None:
                continue
            place = place or hit
            keep = head.split() + tokens[begin + size:]
            return _clean_ws(" ".join(keep)), place
    return _clean_ws(text), place


# --------------------------------------------------------------------------
# 8 - Aufraeumen / Gross-Kleinschreibung
# --------------------------------------------------------------------------

_ACRONYMS = {
    "IT", "AI", "ML", "BI", "QA", "UX", "UI", "HR", "PR", "SEO", "SEM", "SRE",
    "DEV", "OPS", "CRM", "ERP", "SAP", "AWS", "GCP", "SQL", "ETL", "API",
    "CNC", "SPS", "PLC", "HVAC", "CAD", "CAM", "EHS", "HSE", "QHSE", "ESG",
    "B2B", "B2C", "SaaS", "NOC", "SOC", "IoT", "RPA", "LLM", "NLP", "CV",
    "3D", "2D", "KFZ", "LKW", "PKW", "MFA", "PTA", "PDL", "IFRS", "HGB",
    "CEO", "CTO", "CFO", "COO", "CIO", "CISO", "CMO", "CPO", "VP", "GmbH",
    "PHP", "iOS", "QC", "R&D", "M&A", "FP&A", "GTM", "PMO", "SCM", "WMS",
}
_LOWER_WORDS = {"of", "and", "the", "for", "in", "at", "on", "to", "de", "du",
                "der", "die", "das", "und", "im", "am", "von", "mit", "fuer",
                "für", "e", "a", "di", "da", "el", "la", "y"}
_EMPTY_BRACKETS = re.compile(r"[\(\[]\s*[\)\]]")
_JUNK_EDGES = re.compile(r"^[\s\-–|/,.&:•·]+|[\s\-–|/,.&:•·]+$")


def _balance_brackets(text: str) -> str:
    """Unpaarige Klammern entfernen - Reste vom Herausschneiden von Ortsteilen."""
    for open_c, close_c in (("(", ")"), ("[", "]")):
        while text.count(open_c) > text.count(close_c):
            text = text[::-1].replace(open_c, "", 1)[::-1]
        while text.count(close_c) > text.count(open_c):
            text = text.replace(close_c, "", 1)
    return text


def _clean_ws(text: str) -> str:
    text = _EMPTY_BRACKETS.sub(" ", text)
    text = _balance_brackets(text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*/\s*", "/", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?:\s*[-–]\s*){2,}", " - ", text)
    text = re.sub(r"(?:\s*\|\s*){2,}", " | ", text)
    text = re.sub(r"[,;]{2,}", ",", text)
    text = re.sub(r"(?i)^(?:of|de|the|und|and|for|in|at|im|der|die|das)\b\s*", "", text)
    text = re.sub(r"(?i)\s*\b(?:of|de|the|und|and|for|im|der|die|das)$", "", text)
    text = re.sub(r"(?<=\s)['’]s(?=\s|$)", " ", text)
    text = " ".join(t for t in text.split() if t.strip("'\u2019\"`"))
    text = _JUNK_EDGES.sub("", text)
    return text.strip()


def _fix_caps(text: str) -> str:
    """VERKAEUFER TEILZEIT -> Verkaeufer Teilzeit; Akronyme bleiben gross."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4 or any(c.islower() for c in letters):
        return text
    if len(text.split()) == 1:      # einzelnes Kuerzel wie "HRBP" bleibt gross
        return text

    def _word(w: str) -> str:
        bare = w.strip("()[].,/&-")
        if bare.upper() in _ACRONYMS:
            return w
        return w.capitalize() if len(bare) > 1 else w.lower()

    words = text.split()
    out = [_word(w) for w in words]
    for i, w in enumerate(out):
        if i and w.lower() in _LOWER_WORDS:
            out[i] = w.lower()
    return " ".join(out)


# --------------------------------------------------------------------------
# Ergebnis
# --------------------------------------------------------------------------


@dataclass
class CleanedTitle:
    """Ergebnis von :func:`clean_title`."""

    raw: str
    clean: str = ""
    core: str = ""
    seniority: str | None = None
    seniority_hits: list[str] = field(default_factory=list)
    employment_type: str | None = None
    remote_type: str | None = None
    place: Place | None = None
    languages: list[str] = field(default_factory=list)
    had_gender_marker: bool = False
    is_open_application: bool = False

    @property
    def country_iso2(self) -> str | None:
        return self.place.country_iso2 if self.place else None

    @property
    def city(self) -> str | None:
        return self.place.city if self.place else None

    @property
    def region(self) -> str | None:
        return self.place.region if self.place else None

    def as_dict(self) -> dict:
        return {
            "job_title": self.raw,
            "job_title_clean": self.clean,
            "job_title_core": self.core,
            "seniority": self.seniority,
            "employment_type": self.employment_type,
            "remote_type": self.remote_type,
            "country_iso2": self.country_iso2,
            "region": self.region,
            "city": self.city,
            "languages": self.languages,
            "had_gender_marker": self.had_gender_marker,
            "is_open_application": self.is_open_application,
        }


_CACHE: dict[str, CleanedTitle] = {}
_INTERN_NOISE = re.compile(
    r"(?i)\b(?:internship|\w*praktikum|praktikant(?:in|en)?|werkstudent(?:in|en)?|"
    r"working\s+student|praxisstudent(?:in)?|ausbildung(?:splatz)?|azubi|"
    r"auszubildende[rn]?|duales?\s+studium|apprenticeship)\b")


def clean_title(raw: str | None, *, use_cache: bool = True) -> CleanedTitle:
    """Rohtitel saeubern und Attribute extrahieren."""
    if raw is None or not str(raw).strip():
        return CleanedTitle(raw="", clean="", core="")
    raw = str(raw)
    if use_cache and raw in _CACHE:
        return _CACHE[raw]

    text = _normalize_unicode(raw)
    text = _strip_req_ids(text)
    text, had_gender = _strip_gender(text)
    text, languages = _strip_language(text)
    text, employment = _strip_employment(text)
    text, remote = _strip_remote(text)
    text = _strip_noise(text)
    open_app = bool(_OPEN_APPLICATION.search(text))
    text = _OPEN_APPLICATION.sub(" ", text)
    text = _fix_caps(_clean_ws(text))

    # Ort raus - der Titel selbst soll ihn nicht mehr enthalten.
    clean, place = _extract_location(text)
    if not clean:
        clean, place = _clean_ws(text), place

    # Kern zusaetzlich ohne Seniority - das ist der Input fuer den Klassifikator.
    if _ROLE_IS_SENIORITY.match(clean.strip()):
        _, seniority, hits = _extract_seniority(clean)
        core = clean
    else:
        core, seniority, hits = _extract_seniority(clean)
    core = _clean_ws(_INTERN_NOISE.sub(" ", core)) or clean
    clean, core = _fix_caps(clean), _fix_caps(core)

    result = CleanedTitle(
        raw=raw,
        clean=clean,
        core=core,
        seniority=seniority,
        seniority_hits=hits,
        employment_type=employment,
        remote_type=remote,
        place=place,
        languages=languages,
        had_gender_marker=had_gender,
        is_open_application=open_app,
    )
    if use_cache:
        if len(_CACHE) > 400_000:
            _CACHE.clear()
        _CACHE[raw] = result
    return result


def clean_titles(values) -> list[CleanedTitle]:
    """Vektorisierte Variante fuer pandas-Serien (mit Dedup ueber den Cache)."""
    return [clean_title(v) for v in values]
