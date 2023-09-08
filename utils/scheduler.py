from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Optional, Union
from utils.models import Player, Referee, QualifierLobby, BracketMatch
from utils.sheets import get_cells
from utils.sheets import Worksheet, Cell, SheetRange
from config import (
    QUAL_DATE_SHEET_COL,
    QUAL_TIME_SHEET_COL,
    BSTAGE_DATE_SHEET_COL,
    BSTAGE_TIME_SHEET_COL
)
# TODO: combine this and col_idxs into one parameter called config_dict
# or something, less imports are better


class LobbyNotFound(Exception):
    """The lobby cannot be found."""
    pass


class FullLobbyError(Exception):
    """The lobby is full."""
    pass


class SameLobbyError(Exception):
    """The player is already scheduled in the lobby."""
    pass


class NotMatchParticipant(Exception):
    """The player is not a participant of the match."""
    pass


def get_qual_col_order() -> dict[str, int]:
    """
    Return a dictionary mapping each column name to the index
    where the data for the column can be found in a row of cells
    from get_cells().
    """
    # TODO: read this from a config
    # this is temporary
    # remembr this function assumes that all the necessary columns are adjacent
    # to each other in the specified range
    # force hosts to have players at the end, makes things way simpler
    # TODO: look into Enum for this?
    order = ['id', 'date', 'time', 'ref', 'players']
    player_slots = 8

    res = {col_name: i for i, col_name in enumerate(order)}
    res['players_end'] = res['players'] + player_slots - 1
    return res


def get_match_col_order() -> dict[str, int]:
    """
    Same as get_qual_col_order() but for bracket matches.
    """
    order = ['id', 'date', 'time', 'ref', 'empty_column', 'p1', 'p2']
    return {col_name: i for i, col_name in enumerate(order)}


def float_to_datetime(float_days: float) -> datetime:
    """
    Convert <float_days> into a datetime object, where
    <float_days> represents the number of days since December 30th 1899.
    """
    base_date = datetime(1899, 12, 30)
    delta = timedelta(days=float_days)
    result = base_date + delta
    return result


def get_datetime_object(date: float, time: float) -> datetime:
    """
    Create a datetime object from arguments
    formatted by the Google Sheets API.

    If this fails, return a datetime object of January 1, 1970.
    """
    try:
        dt = float_to_datetime(date) + timedelta(days=time)
    except Exception:
        dt = datetime(1970, 1, 1)

    # TODO: maybe let tournament admin pick timezone?
    return dt.replace(tzinfo=timezone.utc)


def row_is_empty(row: list[Cell]) -> bool:
    """
    Return whether or not <row> consists of only empty cells.
    """
    return all([cell.value == '' for cell in row])


def get_player_from_csv(team_name: str = None,
                        discord_name: str = None) -> Optional[Player]:
    """
    Return the Player associated with <team_name> or <discord_name>
    as denoted in the CSV file.

    Exactly one of two arguments should be passed.
    """
    players = pd.read_csv('players.csv')

    # should just be one row from the DataFrame
    if team_name is not None:
        rows = players[players['Team Name'] == team_name]
    elif discord_name is not None:
        rows = players[players['Captain Discord Username'] == discord_name]

    # if not, then that means the entry was not found or
    # there are duplicate team names
    if len(rows) != 1:
        return

    return Player(
        team_name=rows['Team Name'].item(),
        osu_name=rows['Captain osu! Username'].item(),
        discord_name=rows['Captain Discord Username'].item()
    )


def get_referee_from_csv(osu_name: str) -> Optional[Referee]:
    """
    Return the Referee associated with <osu_name> as denoted
    in the CSV file.
    """
    refs = pd.read_csv('refs.csv')

    # should just be one row from the DataFrame
    rows = refs[refs['osu! Username'] == osu_name]

    # if not, then that means the entry was not found in the csv file or
    # there is no ref for the match according to the sheet
    # TODO: due to this error ambiguity, we should warn the admin that if
    # the wrong ref info shows up on the bot, they should verify csv and sheet
    if len(rows) != 1:
        return

    return Referee(
        osu_name=osu_name,
        discord_name=rows['Discord Username'].item()
    )


def find_lobby(lobbies: Union[list[QualifierLobby], list[BracketMatch]],
               id_: str) -> Union[QualifierLobby, BracketMatch, None]:
    """Search <lobbies> for the lobby with <id_>."""
    for lob in lobbies:
        if lob.id == id_:
            return lob


def get_qual_lobbies(worksheet: Worksheet,
                     qual_range: str,
                     col_idxs: dict[str, int]) -> list[QualifierLobby]:
    """
    Return a list of the qualifier lobbies in <worksheet>.
    """
    # TODO: read config file, probably a json (discord security risk?)

    cells = get_cells(
        worksheet=worksheet,
        range_=SheetRange(qual_range),
        col_idxs=col_idxs,
        date_col=QUAL_DATE_SHEET_COL,
        time_col=QUAL_TIME_SHEET_COL
    )

    res: list[QualifierLobby] = []
    for row in cells:
        if row_is_empty(row):
            continue

        players = []
        for i in range(
            col_idxs['players'], col_idxs['players_end'] + 1
        ):
            player = get_player_from_csv(team_name=row[i].value)
            if not player:
                continue
            players.append(player)

        q = QualifierLobby(
            id=row[col_idxs['id']].value,
            time=get_datetime_object(
                row[col_idxs['date']].value,
                row[col_idxs['time']].value
            ),
            players=players,
            slot_count=col_idxs['players_end'] - col_idxs['players'] + 1,
            referee=get_referee_from_csv(row[col_idxs['ref']].value),
            sheet_row=row[0].row
        )
        res.append(q)

    return res


def schedule_qual(worksheet: Worksheet,
                  qual_lobbies: list[QualifierLobby],
                  match_id: str,
                  player: Player,
                  slots_start: str,
                  slots_end: str) -> QualifierLobby:
    """Schedule a player into a qualifier lobby."""
    lobby = find_lobby(qual_lobbies, match_id)

    if not lobby:
        raise LobbyNotFound

    # check if the lobby has room
    if len(lobby) == lobby.slot_count:
        raise FullLobbyError

    # check if the player is already scheduled in a lobby
    old_lobby = None
    for lob in qual_lobbies:
        if player in lob.players:
            old_lobby = lob

    # check if they're scheduled in this one
    if old_lobby == lobby:
        raise SameLobbyError

    # if they're scheduled in a different lobby, remove them from it
    if old_lobby:
        old_lobby.players.remove(player)

    # and then put them in the new lobby
    lobby.players.append(player)

    # update sheet (old lobby)
    if old_lobby:
        worksheet.update(
            f'{slots_start}{old_lobby.sheet_row}:'
            f'{slots_end}{old_lobby.sheet_row}',
            [[p.team_name for p in old_lobby.players] + ['']],
            raw=False
        )

    # update sheet (new lobby)
    worksheet.update(
        f'{slots_start}{lobby.sheet_row}:{slots_end}{lobby.sheet_row}',
        [[p.team_name for p in lobby.players]],
        raw=False
    )

    return lobby


def get_bracket_matches(worksheet: Worksheet,
                        match_range: str,
                        col_idxs: dict[str, int]) -> list[BracketMatch]:
    """
    Return a list of the bracket matches in <worksheet>.
    """
    cells = get_cells(
        worksheet=worksheet,
        range_=SheetRange(match_range),
        col_idxs=col_idxs,
        date_col=BSTAGE_DATE_SHEET_COL,
        time_col=BSTAGE_TIME_SHEET_COL
    )

    return [
        BracketMatch(
            id=row[col_idxs['id']].value,
            time=get_datetime_object(
                row[col_idxs['date']].value,
                row[col_idxs['time']].value
            ),
            player1=get_player_from_csv(team_name=row[col_idxs['p1']].value),
            player2=get_player_from_csv(team_name=row[col_idxs['p2']].value),
            referee=get_referee_from_csv(row[col_idxs['ref']].value),
            sheet_row=row[0].row
        )
        for row in cells
    ]


def validate_reschedule(matches: list[BracketMatch],
                        match_id: str,
                        player: Player) -> BracketMatch:
    """Validate a reschedule request for <match>."""
    match = find_lobby(matches, match_id)

    if not match:
        raise LobbyNotFound

    # check if the player is a match participant
    if player not in [match.player1, match.player2]:
        raise NotMatchParticipant

    return match


def reschedule_match(worksheet: Worksheet,
                     match: BracketMatch,
                     new_time: datetime,
                     date_col: str,
                     time_col: str) -> BracketMatch:
    """
    Reschedule a bracket match.

    <match> must have been validated with <validate_reschedule>.
    """
    # isolate the date and time
    date = new_time.strftime('%a %b %d')
    time = new_time.strftime('%H:%M')

    worksheet.update(f'{date_col}{match.sheet_row}', date, raw=False)
    worksheet.update(f'{time_col}{match.sheet_row}', time, raw=False)

    return match
