import sqlite3


def database_interact(database, query, data=None):
    db = sqlite3.connect(database)
    cur = db.cursor()
    cur.execute("PRAGMA busy_timeout = 30000")
    if not data:
        cur.execute(query)
    else:
        cur.execute(query, data)
    db.commit()
    if 'SELECT' in query:
        stuff = cur.fetchall()
        cur.close()
        return stuff
    cur.close()


class RemindBase:

    def __init__(self, data):
        self.time = data[0]
        self.channel = data[1]
        self.user = data[2]
        self.message = data[3]

    @classmethod
    def remind_create(cls):  # only run on bot start
        database_interact("data/remind.db", "CREATE TABLE IF NOT EXISTS reminders"
                                            "(time integer PRIMARY KEY, channel integer, user integer, message text)")

    @classmethod
    def remind_insert(cls, time, channel, user, msg):
        database_interact("data/remind.db", "INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?)",
                          (time, channel, user, msg,))

    @classmethod
    def remind_grab(cls, current_time):
        get_data = database_interact("data/remind.db", "SELECT * FROM reminders WHERE time < ?", (current_time,))
        database_interact("data/remind.db", "DELETE FROM reminders WHERE time < ?", (current_time,))
        send_data = [RemindBase(result) for result in get_data]
        return send_data
