import sqlite3


class RemindBase:

    def __init__(self, data):
        self.time = data[0]
        self.channel = data[1]
        self.user = data[2]
        self.message = data[3]

    @classmethod
    def create_database(cls):  # only run on bot start
        db = sqlite3.connect('data/remind.db')
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS reminders"
                    "(time integer PRIMARY KEY, channel integer, user integer, message text)")
        db.commit()
        cur.close()

    @classmethod
    def insert_reminder(cls, time, channel, user, msg):
        db = sqlite3.connect('data/remind.db')
        cur = db.cursor()
        cur.execute("PRAGMA busy_timeout = 30000")
        cur.execute("INSERT OR IGNORE INTO reminders VALUES (?, ?, ?, ?)", (time, channel, user, msg,))
        db.commit()
        cur.close()

    @classmethod
    def grab_reminders(cls, current_time):
        db = sqlite3.connect('data/remind.db')
        cur = db.cursor()
        cur.execute("PRAGMA busy_timeout = 30000")
        cur.execute("SELECT * FROM reminders WHERE time < ?", (current_time,))
        data = cur.fetchall()
        cur.execute("DELETE FROM reminders WHERE time < ?", (current_time,))
        db.commit()
        cur.close()
        send_data = []
        for result in data:
            send_data.append(RemindBase(result))
        return send_data
