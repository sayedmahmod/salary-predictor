"""Orts-Normalisierung: freier Text -> (country_iso2, region, city).

Wird an zwei Stellen gebraucht:

1. von :mod:`salarykit.titles.clean`, um einen Ort *aus dem Jobtitel* zu
   erkennen und dort zu entfernen ("Sales Manager (m/w/d) - Zuerich"),
2. von den Quell-Adaptern, um die eigentlichen Ortsfelder zu vereinheitlichen
   ("The Netherlands", "Remote - Seattle, WA", "DE", "Germany").

Bewusst ein handgepflegtes Gazetteer statt einer Geocoding-API: der Build
soll offline und deterministisch laufen.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Laender
# --------------------------------------------------------------------------

#: ISO2 -> englischer Standardname
COUNTRY_NAMES: dict[str, str] = {
    "AE": "United Arab Emirates", "AR": "Argentina", "AT": "Austria",
    "AU": "Australia", "BE": "Belgium", "BG": "Bulgaria", "BR": "Brazil",
    "CA": "Canada", "CH": "Switzerland", "CL": "Chile", "CN": "China",
    "CO": "Colombia", "CR": "Costa Rica", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "EG": "Egypt",
    "ES": "Spain", "FI": "Finland", "FR": "France", "GB": "United Kingdom",
    "GR": "Greece", "HK": "Hong Kong", "HR": "Croatia", "HU": "Hungary",
    "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IN": "India",
    "IS": "Iceland", "IT": "Italy", "JP": "Japan", "KE": "Kenya",
    "KR": "South Korea", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
    "MA": "Morocco", "MT": "Malta", "MX": "Mexico", "MY": "Malaysia",
    "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
    "PE": "Peru", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "KG": "Kyrgyzstan", "KZ": "Kazakhstan", "UZ": "Uzbekistan", "GE": "Georgia (country)",
    "AM": "Armenia", "AZ": "Azerbaijan", "AL": "Albania", "BA": "Bosnia and Herzegovina",
    "MK": "North Macedonia", "ME": "Montenegro", "MD": "Moldova", "BY": "Belarus",
    "LK": "Sri Lanka", "BD": "Bangladesh", "NP": "Nepal", "GH": "Ghana",
    "TZ": "Tanzania", "UG": "Uganda", "ET": "Ethiopia", "DZ": "Algeria",
    "TN": "Tunisia", "JO": "Jordan", "LB": "Lebanon", "QA": "Qatar",
    "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman", "EC": "Ecuador",
    "UY": "Uruguay", "PY": "Paraguay", "BO": "Bolivia", "VE": "Venezuela",
    "GT": "Guatemala", "PA": "Panama", "DO": "Dominican Republic",
    "HN": "Honduras", "SV": "El Salvador", "NI": "Nicaragua",
    "TT": "Trinidad and Tobago", "JM": "Jamaica", "LI": "Liechtenstein",
    "MC": "Monaco", "AD": "Andorra", "SM": "San Marino", "MU": "Mauritius",
    "ZW": "Zimbabwe", "ZM": "Zambia", "SN": "Senegal", "CI": "Cote d'Ivoire",
    "CM": "Cameroon", "AO": "Angola", "MZ": "Mozambique", "RW": "Rwanda",
    "BW": "Botswana", "NA": "Namibia", "KH": "Cambodia", "LA": "Laos",
    "MM": "Myanmar", "MN": "Mongolia", "BN": "Brunei", "MO": "Macau",
    "FJ": "Fiji", "PG": "Papua New Guinea", "IQ": "Iraq", "IR": "Iran",
    "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "RU": "Russia",
    "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia",
    "SK": "Slovakia", "TH": "Thailand", "TR": "Turkey", "TW": "Taiwan",
    "UA": "Ukraine", "US": "United States", "VN": "Vietnam", "ZA": "South Africa",
}

#: alles, was auf ein Land zeigt (Schreibvarianten, DE/FR/IT/ES-Namen,
#: Adjektive) -> ISO2. Keys werden gefaltet (klein, ohne Akzente).
COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US", "u.s.": "US", "u.s.a.": "US", "us": "US", "america": "US",
    "united states": "US", "united states of america": "US", "vereinigte staaten": "US",
    "etats-unis": "US", "estados unidos": "US",
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB",
    "england": "GB", "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "united kingdom": "GB", "grossbritannien": "GB", "vereinigtes koenigreich": "GB",
    "united kingdom of great britain and northern ireland": "GB",
    "germany": "DE", "deutschland": "DE", "allemagne": "DE", "germania": "DE",
    "alemania": "DE", "duitsland": "DE", "german": "DE", "deutsch": "DE",
    "austria": "AT", "oesterreich": "AT", "autriche": "AT",
    "switzerland": "CH", "schweiz": "CH", "suisse": "CH", "svizzera": "CH",
    "netherlands": "NL", "the netherlands": "NL", "niederlande": "NL",
    "holland": "NL", "nederland": "NL", "pays-bas": "NL", "dutch": "NL",
    "france": "FR", "frankreich": "FR", "french": "FR",
    "spain": "ES", "spanien": "ES", "espana": "ES", "espagne": "ES", "spanish": "ES",
    "italy": "IT", "italien": "IT", "italia": "IT", "italie": "IT", "italian": "IT",
    "belgium": "BE", "belgien": "BE", "belgique": "BE", "belgie": "BE",
    "poland": "PL", "polen": "PL", "polska": "PL", "polish": "PL",
    "portugal": "PT", "portuguese": "PT",
    "sweden": "SE", "schweden": "SE", "sverige": "SE",
    "denmark": "DK", "daenemark": "DK", "danmark": "DK",
    "norway": "NO", "norwegen": "NO", "norge": "NO",
    "finland": "FI", "finnland": "FI", "suomi": "FI",
    "ireland": "IE", "irland": "IE", "eire": "IE",
    "czechia": "CZ", "czech republic": "CZ", "tschechien": "CZ", "cesko": "CZ",
    "slovakia": "SK", "slowakei": "SK", "slovenia": "SI", "slowenien": "SI",
    "hungary": "HU", "ungarn": "HU", "magyarorszag": "HU",
    "romania": "RO", "rumaenien": "RO", "bulgaria": "BG", "bulgarien": "BG",
    "greece": "GR", "griechenland": "GR", "croatia": "HR", "kroatien": "HR",
    "serbia": "RS", "serbien": "RS", "estonia": "EE", "estland": "EE",
    "latvia": "LV", "lettland": "LV", "lithuania": "LT", "litauen": "LT",
    "luxembourg": "LU", "luxemburg": "LU", "malta": "MT", "cyprus": "CY",
    "iceland": "IS", "island": "IS",
    "ukraine": "UA", "russia": "RU", "russian federation": "RU",
    "turkey": "TR", "tuerkei": "TR", "turkiye": "TR",
    "israel": "IL", "india": "IN", "indien": "IN", "indian": "IN",
    "pakistan": "PK", "china": "CN", "japan": "JP", "south korea": "KR",
    "korea": "KR", "taiwan": "TW", "hong kong": "HK", "singapore": "SG",
    "singapur": "SG", "malaysia": "MY", "thailand": "TH", "vietnam": "VN",
    "indonesia": "ID", "philippines": "PH", "philippinen": "PH",
    "australia": "AU", "australien": "AU", "new zealand": "NZ", "neuseeland": "NZ",
    "canada": "CA", "kanada": "CA", "mexico": "MX", "mexiko": "MX",
    "brazil": "BR", "brasilien": "BR", "brasil": "BR",
    "argentina": "AR", "argentinien": "AR", "chile": "CL", "colombia": "CO",
    "peru": "PE", "costa rica": "CR",
    "south africa": "ZA", "suedafrika": "ZA", "nigeria": "NG", "kenya": "KE",
    "egypt": "EG", "aegypten": "EG", "morocco": "MA", "marokko": "MA",
    "united arab emirates": "AE", "uae": "AE", "saudi arabia": "SA",
}
COUNTRY_ALIASES.update({
    v.lower(): k for k, v in COUNTRY_NAMES.items()
    if v.lower() not in {"georgia (country)"}
})
COUNTRY_ALIASES["kyrgyzstan"] = "KG"

# --------------------------------------------------------------------------
# Regionen
# --------------------------------------------------------------------------

US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "PR": "Puerto Rico",
}
US_STATE_BY_NAME = {v.lower(): k for k, v in US_STATES.items()}

DE_BUNDESLAENDER = {
    "BW": "Baden-Wuerttemberg", "BY": "Bayern", "BE": "Berlin",
    "BB": "Brandenburg", "HB": "Bremen", "HH": "Hamburg", "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SL": "Saarland",
    "SN": "Sachsen", "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein",
    "TH": "Thueringen",
}

# --------------------------------------------------------------------------
# Staedte -> (Land, Region)
# --------------------------------------------------------------------------

_DE_CITIES = {
    "Berlin": "BE", "Hamburg": "HH", "Muenchen": "BY", "Munich": "BY",
    "Koeln": "NW", "Cologne": "NW", "Frankfurt": "HE", "Frankfurt am Main": "HE",
    "Stuttgart": "BW", "Duesseldorf": "NW", "Dusseldorf": "NW", "Leipzig": "SN",
    "Dortmund": "NW", "Essen": "NW", "Bremen": "HB", "Dresden": "SN",
    "Hannover": "NI", "Hanover": "NI", "Nuernberg": "BY", "Nuremberg": "BY",
    "Duisburg": "NW", "Bochum": "NW", "Wuppertal": "NW", "Bielefeld": "NW",
    "Bonn": "NW", "Muenster": "NW", "Karlsruhe": "BW", "Mannheim": "BW",
    "Augsburg": "BY", "Wiesbaden": "HE", "Moenchengladbach": "NW",
    "Gelsenkirchen": "NW", "Braunschweig": "NI", "Chemnitz": "SN",
    "Kiel": "SH", "Aachen": "NW", "Halle": "ST", "Magdeburg": "ST",
    "Freiburg": "BW", "Krefeld": "NW", "Luebeck": "SH", "Oberhausen": "NW",
    "Erfurt": "TH", "Mainz": "RP", "Rostock": "MV", "Kassel": "HE",
    "Hagen": "NW", "Saarbruecken": "SL", "Potsdam": "BB", "Ludwigshafen": "RP",
    "Oldenburg": "NI", "Leverkusen": "NW", "Osnabrueck": "NI", "Solingen": "NW",
    "Heidelberg": "BW", "Herne": "NW", "Neuss": "NW", "Darmstadt": "HE",
    "Paderborn": "NW", "Regensburg": "BY", "Ingolstadt": "BY", "Wuerzburg": "BY",
    "Fuerth": "BY", "Wolfsburg": "NI", "Offenbach": "HE", "Ulm": "BW",
    "Heilbronn": "BW", "Pforzheim": "BW", "Goettingen": "NI", "Bottrop": "NW",
    "Trier": "RP", "Recklinghausen": "NW", "Reutlingen": "BW", "Bremerhaven": "HB",
    "Koblenz": "RP", "Bergisch Gladbach": "NW", "Jena": "TH", "Remscheid": "NW",
    "Erlangen": "BY", "Moers": "NW", "Siegen": "NW", "Hildesheim": "NI",
    "Salzgitter": "NI", "Cottbus": "BB", "Kaiserslautern": "RP", "Guetersloh": "NW",
    "Schwerin": "MV", "Witten": "NW", "Gera": "TH", "Iserlohn": "NW",
    "Ludwigsburg": "BW", "Esslingen": "BW", "Zwickau": "SN", "Duren": "NW",
    "Ratingen": "NW", "Luedenscheid": "NW", "Marburg": "HE", "Konstanz": "BW",
    "Villingen-Schwenningen": "BW", "Worms": "RP", "Minden": "NW",
    "Neumuenster": "SH", "Norderstedt": "SH", "Delmenhorst": "NI",
    "Bamberg": "BY", "Viersen": "NW", "Gladbeck": "NW", "Rheine": "NW",
    "Troisdorf": "NW", "Loerrach": "BW", "Landshut": "BY", "Aschaffenburg": "BY",
    "Bayreuth": "BY", "Celle": "NI", "Fulda": "HE", "Kempten": "BY",
    "Sindelfingen": "BW", "Friedrichshafen": "BW", "Passau": "BY",
    "Boeblingen": "BW", "Garching": "BY", "Walldorf": "BW", "Eschborn": "HE",
    "Unterfoehring": "BY", "Wolfratshausen": "BY", "Neu-Isenburg": "HE",
}
_AT_CITIES = ["Wien", "Vienna", "Graz", "Linz", "Salzburg", "Innsbruck",
              "Klagenfurt", "Villach", "Wels", "Sankt Poelten", "Dornbirn"]
_CH_CITIES = ["Zuerich", "Zurich", "Genf", "Geneva", "Geneve", "Basel", "Bern",
              "Lausanne", "Winterthur", "Luzern", "Lucerne", "St. Gallen",
              "Lugano", "Zug", "Baar", "Biel"]

_CITY_COUNTRY: dict[str, str] = {}
_CITY_REGION: dict[str, str] = {}
for _c, _r in _DE_CITIES.items():
    _CITY_COUNTRY[_c] = "DE"
    _CITY_REGION[_c] = DE_BUNDESLAENDER[_r]
for _c in _AT_CITIES:
    _CITY_COUNTRY[_c] = "AT"
for _c in _CH_CITIES:
    _CITY_COUNTRY[_c] = "CH"

_OTHER_CITIES: dict[str, str] = {
    # NL / BE / LU
    "Amsterdam": "NL", "Rotterdam": "NL", "Utrecht": "NL", "Eindhoven": "NL",
    "The Hague": "NL", "Den Haag": "NL", "Groningen": "NL", "Delft": "NL",
    "Tilburg": "NL", "Almere": "NL", "Haarlem": "NL", "Nijmegen": "NL",
    "Brussels": "BE", "Bruessel": "BE", "Bruxelles": "BE", "Antwerp": "BE",
    "Antwerpen": "BE", "Ghent": "BE", "Gent": "BE", "Leuven": "BE",
    "Liege": "BE", "Charleroi": "BE", "Luxembourg City": "LU",
    # FR
    "Paris": "FR", "Lyon": "FR", "Marseille": "FR", "Toulouse": "FR",
    "Nice": "FR", "Nantes": "FR", "Montpellier": "FR", "Strasbourg": "FR",
    "Bordeaux": "FR", "Lille": "FR", "Rennes": "FR", "Grenoble": "FR",
    "Sophia Antipolis": "FR", "Toulon": "FR", "Angers": "FR", "Dijon": "FR",
    "Clermont Ferrand": "FR", "Clermont-Ferrand": "FR", "Le Mans": "FR",
    # UK / IE
    "London": "GB", "Manchester": "GB", "Birmingham": "GB", "Leeds": "GB",
    "Glasgow": "GB", "Edinburgh": "GB", "Liverpool": "GB", "Bristol": "GB",
    "Sheffield": "GB", "Cardiff": "GB", "Belfast": "GB", "Newcastle": "GB",
    "Nottingham": "GB", "Leicester": "GB", "Cambridge": "GB", "Oxford": "GB",
    "Brighton": "GB", "Reading": "GB", "Southampton": "GB", "Coventry": "GB",
    "Aberdeen": "GB", "Milton Keynes": "GB", "Tunbridge Wells": "GB",
    "Dublin": "IE", "Cork": "IE", "Galway": "IE", "Limerick": "IE",
    # ES / PT / IT
    "Madrid": "ES", "Barcelona": "ES", "Valencia": "ES", "Seville": "ES",
    "Sevilla": "ES", "Bilbao": "ES", "Malaga": "ES", "Zaragoza": "ES",
    "Lisbon": "PT", "Lisboa": "PT", "Porto": "PT", "Braga": "PT",
    "Milan": "IT", "Milano": "IT", "Rome": "IT", "Roma": "IT", "Turin": "IT",
    "Torino": "IT", "Naples": "IT", "Napoli": "IT", "Bologna": "IT",
    "Florence": "IT", "Firenze": "IT", "Venice": "IT", "Venezia": "IT",
    "Bergamo": "IT", "Padova": "IT", "Verona": "IT", "Genoa": "IT",
    # Nordics / Baltics
    "Stockholm": "SE", "Gothenburg": "SE", "Goeteborg": "SE", "Malmoe": "SE",
    "Uppsala": "SE", "Copenhagen": "DK", "Kopenhagen": "DK", "Koebenhavn": "DK",
    "Aarhus": "DK", "Odense": "DK", "Oslo": "NO", "Bergen": "NO",
    "Trondheim": "NO", "Stavanger": "NO", "Helsinki": "FI", "Espoo": "FI",
    "Tampere": "FI", "Reykjavik": "IS", "Tallinn": "EE", "Tartu": "EE",
    "Riga": "LV", "Vilnius": "LT", "Kaunas": "LT",
    # CEE
    "Warsaw": "PL", "Warszawa": "PL", "Warschau": "PL", "Krakow": "PL",
    "Krakau": "PL", "Wroclaw": "PL", "Poznan": "PL", "Gdansk": "PL",
    "Lodz": "PL", "Katowice": "PL", "Prague": "CZ", "Praha": "CZ",
    "Prag": "CZ", "Brno": "CZ", "Ostrava": "CZ", "Bratislava": "SK",
    "Kosice": "SK", "Budapest": "HU", "Debrecen": "HU", "Bucharest": "RO",
    "Bukarest": "RO", "Cluj-Napoca": "RO", "Timisoara": "RO", "Iasi": "RO",
    "Sofia": "BG", "Plovdiv": "BG", "Belgrade": "RS", "Beograd": "RS",
    "Zagreb": "HR", "Ljubljana": "SI", "Athens": "GR", "Athen": "GR",
    "Thessaloniki": "GR", "Kyiv": "UA", "Kiev": "UA", "Lviv": "UA",
    "Kharkiv": "UA", "Odesa": "UA", "Dnipro": "UA", "Istanbul": "TR",
    "Ankara": "TR", "Izmir": "TR", "Moscow": "RU", "Saint Petersburg": "RU",
    # Americas
    "New York": "US", "New York City": "US", "San Francisco": "US",
    "Los Angeles": "US", "Chicago": "US", "Seattle": "US", "Boston": "US",
    "Austin": "US", "Denver": "US", "Atlanta": "US", "Dallas": "US",
    "Houston": "US", "Phoenix": "US", "San Diego": "US", "San Jose": "US",
    "Portland": "US", "Miami": "US", "Philadelphia": "US", "Minneapolis": "US",
    "Detroit": "US", "Washington DC": "US", "Pittsburgh": "US",
    "Salt Lake City": "US", "Raleigh": "US", "Charlotte": "US",
    "Nashville": "US", "Columbus": "US", "Cheyenne": "US", "Sarasota": "US",
    "Palo Alto": "US", "Mountain View": "US", "Sunnyvale": "US",
    "Santa Clara": "US", "Cupertino": "US", "Redmond": "US", "Bellevue": "US",
    "Brooklyn": "US", "Toronto": "CA", "Vancouver": "CA", "Montreal": "CA",
    "Ottawa": "CA", "Calgary": "CA", "Edmonton": "CA", "Waterloo": "CA",
    "Mexico City": "MX", "Guadalajara": "MX", "Monterrey": "MX",
    "Sao Paulo": "BR", "Rio de Janeiro": "BR", "Buenos Aires": "AR",
    "Santiago": "CL", "Bogota": "CO", "Lima": "PE",
    # APAC / MEA
    "Bangalore": "IN", "Bengaluru": "IN", "Mumbai": "IN", "Delhi": "IN",
    "New Delhi": "IN", "Hyderabad": "IN", "Pune": "IN", "Chennai": "IN",
    "Gurgaon": "IN", "Gurugram": "IN", "Noida": "IN", "Kolkata": "IN",
    "Ahmedabad": "IN", "Singapore": "SG", "Hong Kong": "HK", "Tokyo": "JP",
    "Osaka": "JP", "Seoul": "KR", "Taipei": "TW", "Shanghai": "CN",
    "Beijing": "CN", "Shenzhen": "CN", "Bangkok": "TH", "Jakarta": "ID",
    "Manila": "PH", "Kuala Lumpur": "MY", "Ho Chi Minh City": "VN",
    "Hanoi": "VN", "Sydney": "AU", "Melbourne": "AU", "Brisbane": "AU",
    "Perth": "AU", "Adelaide": "AU", "Canberra": "AU", "Auckland": "NZ",
    "Wellington": "NZ", "Tel Aviv": "IL", "Jerusalem": "IL", "Haifa": "IL",
    "Dubai": "AE", "Abu Dhabi": "AE", "Riyadh": "SA", "Cairo": "EG",
    "Casablanca": "MA", "Cape Town": "ZA", "Johannesburg": "ZA",
    "Nairobi": "KE", "Lagos": "NG", "Karachi": "PK", "Lahore": "PK",
    "Islamabad": "PK", "Bishkek": "KG",
}
for _c, _cc in _OTHER_CITIES.items():
    _CITY_COUNTRY[_c] = _cc

_US_CITY_STATE = {
    "New York": "NY", "New York City": "NY", "Brooklyn": "NY",
    "San Francisco": "CA", "Los Angeles": "CA", "San Diego": "CA",
    "San Jose": "CA", "Palo Alto": "CA", "Mountain View": "CA",
    "Sunnyvale": "CA", "Santa Clara": "CA", "Cupertino": "CA",
    "Chicago": "IL", "Seattle": "WA", "Redmond": "WA", "Bellevue": "WA",
    "Boston": "MA", "Austin": "TX", "Dallas": "TX", "Houston": "TX",
    "Denver": "CO", "Atlanta": "GA", "Phoenix": "AZ", "Portland": "OR",
    "Miami": "FL", "Sarasota": "FL", "Philadelphia": "PA", "Pittsburgh": "PA",
    "Minneapolis": "MN", "Detroit": "MI", "Washington DC": "DC",
    "Salt Lake City": "UT", "Raleigh": "NC", "Charlotte": "NC",
    "Nashville": "TN", "Columbus": "OH", "Cheyenne": "WY",
}
for _c, _s in _US_CITY_STATE.items():
    _CITY_REGION[_c] = US_STATES[_s]


_UMLAUT_EXPANSION = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe",
                     "Ü": "Ue", "ß": "ss", "å": "aa", "æ": "ae", "ø": "oe"}


def fold(text: str) -> str:
    """klein, ohne Akzente, ohne doppelte Leerzeichen - fuer Lookups."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = t.replace("ß", "ss")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower().replace("\u2019", "'")
    return re.sub(r"\s+", " ", t).strip()


def fold_variants(text: str) -> set[str]:
    """Beide gaengigen Umschriften: "Muenchen" und "Munchen" zeigen auf dasselbe.

    Ohne das findet ein Lookup auf "Muenchen" den Eintrag "Munchen" nicht - im
    Datensatz kommen beide Schreibweisen vor.
    """
    if not text:
        return set()
    expanded = "".join(_UMLAUT_EXPANSION.get(c, c) for c in str(text))
    return {v for v in (fold(text), fold(expanded)) if v}


#: gefaltete Stadtform -> kanonische Schreibweise
CITY_LOOKUP: dict[str, str] = {v: c for c in _CITY_COUNTRY for v in fold_variants(c)}
#: gefaltete Landform -> ISO2
COUNTRY_LOOKUP: dict[str, str] = {
    v: iso for k, iso in COUNTRY_ALIASES.items() for v in fold_variants(k)
}
#: alles, was ein Ort sein kann (fuer den Titel-Cleaner)
PLACE_LOOKUP: dict[str, tuple[str, str]] = {}
for _k, _v in COUNTRY_LOOKUP.items():
    PLACE_LOOKUP[_k] = ("country", _v)
for _k, _v in CITY_LOOKUP.items():
    PLACE_LOOKUP.setdefault(_k, ("city", _v))
for _abbr, _name in US_STATES.items():
    for _v in fold_variants(_name):
        PLACE_LOOKUP.setdefault(_v, ("region", _name))
for _name in DE_BUNDESLAENDER.values():
    for _v in fold_variants(_name):
        PLACE_LOOKUP.setdefault(_v, ("region", _name))

#: laengste Ortsbezeichnung in Tokens - begrenzt das n-Gram-Fenster im Cleaner
MAX_PLACE_TOKENS = max(len(k.split()) for k in PLACE_LOOKUP)


#: Schreibvarianten derselben Stadt auf eine kanonische Form ziehen, damit
#: "Munich" und "Muenchen" spaeter nicht zwei Gruppen bilden.
CITY_CANONICAL: dict[str, str] = {
    "Munich": "Muenchen", "Cologne": "Koeln", "Dusseldorf": "Duesseldorf",
    "Hanover": "Hannover", "Nuremberg": "Nuernberg", "Vienna": "Wien",
    "Zurich": "Zuerich", "Geneva": "Genf", "Geneve": "Genf",
    "Lucerne": "Luzern", "Bruessel": "Brussels", "Bruxelles": "Brussels",
    "Antwerpen": "Antwerp", "Gent": "Ghent", "Den Haag": "The Hague",
    "Milano": "Milan", "Roma": "Rome", "Torino": "Turin", "Napoli": "Naples",
    "Firenze": "Florence", "Venezia": "Venice", "Lisboa": "Lisbon",
    "Sevilla": "Seville", "Warszawa": "Warsaw", "Warschau": "Warsaw",
    "Krakau": "Krakow", "Praha": "Prague", "Prag": "Prague",
    "Bukarest": "Bucharest", "Beograd": "Belgrade", "Athen": "Athens",
    "Kiev": "Kyiv", "Kopenhagen": "Copenhagen", "Koebenhavn": "Copenhagen",
    "Goeteborg": "Gothenburg", "Bengaluru": "Bangalore", "Gurugram": "Gurgaon",
    "New Delhi": "Delhi", "New York City": "New York",
    "Clermont-Ferrand": "Clermont Ferrand", "Frankfurt am Main": "Frankfurt",
}


@dataclass(frozen=True)
class Place:
    country_iso2: str | None = None
    country_name: str | None = None
    region: str | None = None
    city: str | None = None

    @property
    def empty(self) -> bool:
        return not (self.country_iso2 or self.region or self.city)

    def label(self) -> str:
        return ", ".join(p for p in (self.city, self.region, self.country_name) if p)


def _country(iso2: str | None) -> tuple[str | None, str | None]:
    if not iso2:
        return None, None
    return iso2, COUNTRY_NAMES.get(iso2, iso2)


def lookup_place(token: str) -> Place | None:
    """Ein einzelnes (bereits getrimmtes) Fragment nachschlagen."""
    hit = None
    for key in fold_variants(token):
        hit = PLACE_LOOKUP.get(key)
        if hit is not None:
            break
    if hit is None:
        return None
    kind, value = hit
    if kind == "country":
        iso, name = _country(value)
        return Place(country_iso2=iso, country_name=name)
    if kind == "city":
        iso, name = _country(_CITY_COUNTRY.get(value))
        region = _CITY_REGION.get(value)
        canonical = CITY_CANONICAL.get(value, value)
        return Place(country_iso2=iso, country_name=name,
                     region=region or _CITY_REGION.get(canonical), city=canonical)
    # region
    iso = "US" if value.lower() in US_STATE_BY_NAME else "DE"
    iso, name = _country(iso)
    return Place(country_iso2=iso, country_name=name, region=value)


_REMOTE_WORDS = {
    "remote", "remote eu", "remote us", "remote emea", "fully remote",
    "hybrid", "onsite", "on site", "anywhere", "worldwide", "global",
    "home office", "homeoffice", "wfh", "flexible", "various", "multiple",
    "eu", "emea", "europe", "europa", "apac", "americas", "worldwide remote",
}
_SPLIT = re.compile(r"\s*(?:[|/;·•]|,|–|—| - | ‐ )\s*")


def parse_location(raw: str | None, default_country: str | None = None) -> Place:
    """Freies Ortsfeld ("Remote - Seattle, WA", "The Netherlands") aufloesen.

    Nimmt das spezifischste, was gefunden wird: Stadt schlaegt Region schlaegt
    Land. Widerspruechliche Laender werden zugunsten des ersten Treffers
    aufgeloest.
    """
    if raw is None or (isinstance(raw, float)) or not str(raw).strip():
        iso, name = _country(default_country)
        return Place(country_iso2=iso, country_name=name)

    text = re.sub(r"\s+", " ", str(raw)).strip()
    parts = [p.strip(" ()[]") for p in _SPLIT.split(text) if p.strip(" ()[]")]

    city = region = None
    iso2 = None
    for part in parts:
        if fold(part) in _REMOTE_WORDS:
            continue
        # "WA" / "CA" als US-Bundesstaat-Kuerzel
        if len(part) == 2 and part.isupper() and part in US_STATES:
            region = region or US_STATES[part]
            iso2 = iso2 or "US"
            continue
        if len(part) == 2 and part.isupper() and part in COUNTRY_NAMES:
            iso2 = iso2 or part
            continue
        place = lookup_place(part)
        if place is None:
            continue
        city = city or place.city
        region = region or place.region
        iso2 = iso2 or place.country_iso2

    iso2 = iso2 or default_country
    iso, name = _country(iso2)
    return Place(country_iso2=iso, country_name=name, region=region, city=city)


def normalize_country(raw: str | None) -> tuple[str | None, str | None]:
    """Nur das Land aus einem Landfeld ziehen."""
    if raw is None or not str(raw).strip():
        return None, None
    text = str(raw).strip()
    if len(text) == 2 and text.upper() in COUNTRY_NAMES:
        return _country(text.upper())
    for key in fold_variants(text):
        iso = COUNTRY_LOOKUP.get(key)
        if iso:
            return _country(iso)
    return None, None
