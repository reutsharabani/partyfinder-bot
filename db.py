import sqlite3
import logging

logger = logging.getLogger("db")

db_file_name = 'partyfinder.db'
conn = sqlite3.connect(db_file_name)

# conn.execute("drop table if exists players")
conn.execute("create table if not exists players ("
             "discord_id int primary key,"
             "mmr int)")

# conn.execute("drop table if exists positions")
conn.execute("create table if not exists player_positions ("
             "discord_id int,"
             "position int,"
             "PRIMARY KEY (discord_id, position))")


def register(discord_id, mmr):
    conn.execute("insert into players(discord_id, mmr) "
                 f"values ('{discord_id}', '{mmr}')")
    for position in range(1,6):
        conn.execute("insert into player_positions(discord_id, position) "
                     f"values ('{discord_id}', '{position}')")
    conn.commit()


def get_mmr(discord_id):
    mmr = list(conn.execute("select mmr "
                            "from players "
                            f"where discord_id = '{discord_id}'"))
    if mmr:
        return mmr[0][0]


def get_positions(discord_id):
    rows = sorted(conn.execute("select position "
                             "from player_positions "
                             f"where discord_id = '{discord_id}'"))
    if rows:
        return {row[0] for row in rows}


def update_mmr(discord_id, mmr):
    logger.warning(f'setting {discord_id} mmr to {mmr}')
    conn.execute(f"update players set mmr = {mmr} where discord_id = {discord_id}")
    conn.commit()


def add_position(discord_id, position):
    conn.execute(f"insert into player_positions (discord_id, position) VALUES ({discord_id}, {position})")
    conn.commit()


def remove_position(discord_id, position):
    conn.execute(f"delete from player_positions where discord_id = {discord_id} and position = {position}")
    conn.commit()


def delete_player(discord_id):
    logger.warning(f'delete player {discord_id}')
    conn.execute(f"delete from player_positions where discord_id = '{discord_id}'")
    conn.execute(f"delete from players where discord_id = '{discord_id}'")
    conn.commit()


def relevant_players(discord_id, mmr_diff):
    user_positions = (get_positions(discord_id) or set())
    wanted_positions = {1, 2, 3, 4, 5} - user_positions
    mmr = get_mmr(discord_id)
    if len(user_positions) != 1:
        wanted_positions = {1, 2, 3, 4, 5}
    logger.warning(f'find relevant players for {mmr} {wanted_positions} {mmr_diff}')
    min_mmr = mmr - mmr_diff
    max_mmr = mmr + mmr_diff
    players = set(conn.execute(f"select players.discord_id, players.mmr "
                               f"from players "
                               f"join player_positions "
                               f"on player_positions.discord_id = players.discord_id "
                               f"where players.mmr < '{max_mmr}' "
                               f"and players.discord_id != {discord_id} "
                               f"and players.mmr > '{min_mmr}' "
                               f"and player_positions.position in ({','.join(map(str, wanted_positions))})"))
    logger.warning(f'players {players}')
    return players


def players():
    return list(conn.execute(f'select * from players'))


def backup(target):
    def progress(_, remaining, total):
        print(f'Copied {total-remaining} of {total} pages...')
    with sqlite3.connect(target) as bck:
        conn.backup(bck, pages=1, progress=progress)
    return target


def close_connection():
    conn.close()


def open_connection():
    global conn
    conn = sqlite3.connect(db_file_name)
    return conn