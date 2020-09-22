#!/usr/bin/env python3


from _exceptions import RecordMappingError
from numpy import NaN
from isbnlib import canonical as isbn_canonical
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


def merge_data(data, dbkk):
    """Merge values from dbkk into data, if the value in data is empty.

    Also returns the updated values in a separate dict, so we can update
    openlibrary with the missing data

    Test if dict is empty:
    bool({}) -> False
    not {} -> True
    len({}) -> 0
    """
    # this does not work; we need to treat empty strings
    # return {**dbkk, **data}

    updated = {}
    res = data.copy()
    for k,v in dbkk.items():
        if k not in data or data[k] == '':
            res[k] = v
            updated[k] = v
    return res, updated


def query(records):
    isbn = isbn_canonical(records.get("ISBN-nr", ""))
    title = records.get("Titel", "")
    try:
        canonical = {}
        canonical["ISBN-13"] = isbn
        canonical["Title"] = title
        canonical["Publisher"] = records.get("Forlag", "")
        canonical["Year"] = records.get("Årstal")
        sprog = records.get("Sprog", "")
        canonical["Language"] = sprog_map.get(sprog, "")
        canonical["Cover"] = ""
        canonical["Pages"] = records.get("Sideantal", "")
        canonical["Categories"] = records.get("Beskrivelse", "")
        canonical["Description"] = ""
        canonical["Preview"] = ""

        # in DBKK db, the authors might be in 'last, first'-name.
        # lets reverse that
        author = records.get("Forfatter", "")
        if author.find(",") != -1:
            author = " ".join(author.split(", ")[::-1])
        canonical["Authors"] = author

        # loc_id : placering paa hylden
        loc_id = LOC_TABLE[records["Beskrivelse"]]
        if loc_id == LOC_TABLE["Område/Guide/Ekspedition"]:
            loc_id = f"{loc_id}.{COUNTRY_TABLE[records['Land']]}"

        canonical["Location"] = loc_id

    except Exception:  # pragma: no cover
        LOGGER.debug(
            "RecordMappingError for (%s, %s) with data %s", isbn, title, records
        )
        raise RecordMappingError(isbn, title)
    return canonical
