"""Emit an anonymous workbook to stdout for the browser integration test, never disk."""

import base64

from tests.fixtures import workbook

if __name__ == "__main__":

    def add_person(book):
        sheet = book["PLANILLA"]
        for col in range(1, 41):
            sheet.cell(13, col).value = sheet.cell(7, col).value
        sheet["A13"] = 2
        sheet["B13"] = "S-002"
        sheet["C13"] = "Segunda persona"
        sheet["F13"] = "Operaciones"

    print(base64.b64encode(workbook(add_person)).decode("ascii"))
