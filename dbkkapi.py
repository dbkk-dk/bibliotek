#!/usr/bin/env python3


from _exceptions import RecordMappingError
from numpy import NaN
from isbnlib import canonical as isbn_canonical, is_isbn10, is_isbn13
import logging

LOGGER = logging.getLogger(__name__)

# Oversæt sprog til engelsk, eg. key, value mapping
sprog_da = [
    "Fransk",
    "Dansk",
    "Engelsk",
    "Tysk",
    "Norsk",
    "Svensk",
    "Spansk",
    "Tjekkisk",
    "Slovensk",
    "Italiensk",
    "Engelsk++",
    "Tysk/Fransk",
    "Polsk",
    "Portugisisk",
    "Engelsk/japansk",
    "Islandsk",
    NaN,
]
sprog_en = [
    "French",
    "Danish",
    "English",
    "German",
    "Norwegian",
    "Swedish",
    "Spanish",
    "Czech",
    "Slovenian",
    "Italian",
    "English",
    "German/French",
    "Polish",
    "Portuguese",
    "English/Japanese",
    "Icelandic",
    "",
]
sprog_map = dict(zip(sprog_da, sprog_en))

LOC_TABLE = {
    "Biografi/Erindringer/Historie": 5,
    "Blandet indhold": 6,
    "Fiktion": 3,
    "Håndbog/Medicin/Sikkerhed": 4,
    "Lærebog/Instruktion": 1,
    "Område/Guide/Ekspedition": 2,  # Se country herunder for underkategori
}

# fundet ved
# df2.Land.unique()
# df2.Sprog.unique()
COUNTRY_TABLE = {
    "Hele verden": 0,
    "Europa": 1,
    "Frankrig": 2,
    "Schweiz": 3,
    "Tyskland": 4,
    "Østrig": 5,
    "Italien": 6,
    "Grønland/Island/Arktis": 7,
    "Norge": 8,
    "Sverige": 9,
    "Storbritanien": 10,
    "Spanien/Portugal": 11,
    "Asien": 12,  # everest
    "Australien/New Zealand/Antarktis": 13,
    "Sydamerika": 14,
    "Nordamerika": 15,
    "Afrika": 16,
    "Tatra": 17,  # Balkan?
    "Balkan": 18,  # bør nok høre under europa, men det kan altid opdateres
    "Andre": 19,
    "Everest": 20,  # bliver ikke brugt i databasen. Everest under Asien. Dette er nok Antartica
    NaN: 21,
}


def query(records):
    isbn = isbn_canonical(records.get("ISBN-nr", ""))
    title = records.get("Titel", "")
    try:
        canonical = {}
        canonical["isbn"] = isbn
        canonical["title"] = title
        canonical["publisher"] = records.get("Forlag", "")
        canonical["year"] = records.get("Årstal")
        sprog = records.get("Sprog", "")
        canonical["language"] = sprog_map.get(sprog, "")
        canonical["thumbnail"] = ""
        canonical["pages"] = records.get("Sideantal", "")
        canonical["categories"] = records.get("Beskrivelse", "")
        canonical["description"] = ""
        canonical["preview_url"] = ""

        # in DBKK db, the authors might be in 'last, first'-name.
        # lets reverse that
        author = records.get("Forfatter", "")
        if author.find(",") != -1:
            author = " ".join(author.split(", ")[::-1])
        canonical["authors"] = author

        # loc_id : placering paa hylden
        loc_id = LOC_TABLE[records["Beskrivelse"]]
        if loc_id == LOC_TABLE["Område/Guide/Ekspedition"]:
            loc_id = f"{loc_id}.{COUNTRY_TABLE[records['Land']]}"
        canonical["location"] = loc_id

        if is_isbn10(isbn):
            canonical["isbn_10"] = isbn
        elif is_isbn13(isbn):
            canonical["isbn_13"] = isbn
        else:
            LOGGER.debug(f"isbn {isbn} is neither isbn10 or isbn13.\n{records}")
            # raise KeyError(f"isbn {isbn} is neither isbn10 or isbn13")

    except Exception:  # pragma: no cover
        LOGGER.debug(
            "RecordMappingError for (%s, %s) with data %s", isbn, title, records
        )
        raise RecordMappingError(isbn, title)
    return canonical
