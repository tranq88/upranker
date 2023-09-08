from __future__ import annotations
from datetime import datetime
from typing import Optional


class Player:
    """
    An osu! tournament player.
    Represents either a solo player or an entire team.

    In a 1v1 setting, <team_name> should be the same as <osu_name>.

    In a team setting, <osu_name> and <discord_id> should be
    the osu! username and Discord ID of the team captain, respectively.
    """
    def __init__(self, team_name: str, osu_name: str, discord_name: str):
        self.team_name = team_name
        self.osu_name = osu_name
        self.discord_name = discord_name

    def __eq__(self, other: Player) -> bool:
        return (
            self.team_name == other.team_name and
            self.osu_name == other.osu_name and
            self.discord_name == other.discord_name
        )


class Referee:
    """An osu! tournament referee."""
    def __init__(self, osu_name: str, discord_name: str):
        self.osu_name = osu_name
        self.discord_name = discord_name


class Lobby:
    """An osu! tournament lobby."""
    def __init__(self,
                 id: str,
                 time: datetime,
                 referee: Optional[Referee],
                 sheet_row: int):
        self.id = id
        self.time = time
        self.referee = referee
        self.sheet_row = sheet_row


class QualifierLobby(Lobby):
    """An osu! tournament qualifier lobby."""
    def __init__(self,
                 id: str,
                 time: datetime,
                 players: list[Player],
                 slot_count: int,
                 referee: Optional[Referee],
                 sheet_row: int):
        super().__init__(id, time, referee, sheet_row)
        self.players = players
        self.slot_count = slot_count  # len(self.players) <= self.slot_count

    def __len__(self) -> int:
        return len(self.players)

    def __bool__(self) -> bool:
        return True


class BracketMatch(Lobby):
    """An osu! tournament bracket match."""
    def __init__(self,
                 id: str,
                 time: datetime,
                 player1: Player,
                 player2: Player,
                 referee: Optional[Referee],
                 sheet_row: int):
        super().__init__(id, time, referee, sheet_row)
        self.player1 = player1
        self.player2 = player2
