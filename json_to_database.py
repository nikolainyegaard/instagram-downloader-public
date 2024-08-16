import json
import sqlite3
import database_functions

def convert_database_from_json(cursor, path):
    with open(path, "r") as f:
        old_data = json.load(f)

    
    for key in old_data["users"]:
        user = old_data["users"][key]
        try:
            cursor.execute('''
            INSERT INTO users (user_id, username, downloads)
            VALUES (?, ?, ?)
            ''', (user["user_id"], user["username"], user["downloads"]))
        except sqlite3.IntegrityError:
            cursor.execute('''
            UPDATE users
            SET username = ?, downloads = ?
            WHERE user_id = ?
            ''', (user["username"], user["downloads"], user["user_id"]))
        try:
            cursor.execute('''
            INSERT INTO preferences (user_id, priority, queue_alerts)
            VALUES (?, ?, ?)
            ''', (user["user_id"], user["preferences"]["priority"], user["preferences"]["queue_alerts"]))
        except sqlite3.IntegrityError:
            cursor.execute('''
            UPDATE preferences
            SET priority = ?, queue_alerts = ?
            WHERE user_id = ?
            ''', (user["preferences"]["priority"], user["preferences"]["queue_alerts"], user["user_id"]))
        for download in user["downloaded_posts"]:
            hash = database_functions.generate_unique_id(user["user_id"], download["uploader"])
            cursor.execute('''
            SELECT 1 FROM downloaded_posts
            WHERE hash = ?
            ''', (hash,))
            result = cursor.fetchone()
            if result is None:
                cursor.execute('''
                INSERT INTO downloaded_posts (hash, user_id, uploader, downloads)
                VALUES (?, ?, ?, ?)
                ''', (hash, user["user_id"], download["uploader"], download["downloads"]))
            else:
                cursor.execute('''
                UPDATE downloaded_posts
                SET downloads = ?
                WHERE hash = ?
                ''', (download["downloads"], hash))
    cursor.connection.commit()