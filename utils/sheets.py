import gspread
from gspread.worksheet import Worksheet, Cell


class SheetRange:
    """
    A Google Sheets spreadsheet range of the format XY:XY,
    where X is the column letter and Y is the row number.
    """
    def __init__(self, full_range: str):
        self.full_range = full_range

        self.start_name = full_range.split(':')[0]
        self.end_name = full_range.split(':')[1]

        self.start_col = self.start_name.rstrip('0123456789')
        self.end_col = self.end_name.rstrip('0123456789')

        self.start_row = self.start_name[len(self.start_col):]
        self.end_row = self.end_name[len(self.end_col):]


def get_worksheet(spreadsheet_key: str, worksheet_name: str) -> Worksheet:
    """
    Access the Google Sheets API and return the Worksheet
    specified by <spreadsheet_key> and <worksheet_name>.

    The service account must have access to the spreadsheet.
    """
    sa = gspread.service_account(filename='service_account.json')
    sh = sa.open_by_key(spreadsheet_key)
    return sh.worksheet(worksheet_name)


def get_cells(worksheet: Worksheet,
              range_: SheetRange,
              col_idxs: dict[str, int],
              date_col: str,
              time_col: str) -> list[list[Cell]]:
    """Get the cells specified by <range_> from <worksheet>."""
    # get the cell objects because it includes empty cells
    cells = worksheet.range(range_.full_range)

    # convert <cells> into a 2D list by rows
    rows: dict[int, list[Cell]] = {}
    for cell in cells:
        if cell.row not in rows:
            rows[cell.row] = []
        rows[cell.row].append(cell)

    cells = list(rows.values())

    # get the cell values because we want UNFORMATTED_VALUE
    values = worksheet.batch_get(
        [
            f'{date_col}{range_.start_row}:{date_col}{range_.end_row}',
            f'{time_col}{range_.start_row}:{time_col}{range_.end_row}'
        ],
        value_render_option='UNFORMATTED_VALUE'
    )

    # update the cell objects with the unformatted values
    date_values = values[0]
    time_values = values[1]
    for i, (date, time) in enumerate(zip(date_values, time_values)):
        # i = the current row
        # we need to reference the 0th index because <date> and <time>
        # are lists of size 1
        cells[i][col_idxs['date']].value = date[0]
        cells[i][col_idxs['time']].value = time[0]

    return cells
