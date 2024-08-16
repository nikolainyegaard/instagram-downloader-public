import hashlib

def create_tables(cursor):
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stats (
        total_downloads INTEGER,
        total_users INTEGER,
        downloads_today INTEGER,
        new_users_today INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS command_stats (
        command TEXT PRIMARY KEY,
        count INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        downloads INTEGER
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS former_usernames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        former_username TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checked_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS downloaded_posts (
        hash INTEGER PRIMARY KEY,
        user_id INTEGER,
        uploader TEXT,
        downloads INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS preferences (
        user_id INTEGER PRIMARY KEY,
        priority INTEGER,
        queue_alerts BOOLEAN,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        user_priority INTEGER,
        username TEXT,
        media_pk TEXT,
        media_type_int INTEGER,
        media_type_str TEXT,
        author_id TEXT,
        media_number INTEGER,
        youtube_id TEXT
    )
    ''')

def generate_unique_id(user_id, post_id):
    combined_id = f"{user_id}{post_id}"
    return int(hashlib.sha256(combined_id.encode()).hexdigest()[:15], 16)

def get_priority(cursor, user_id):
    cursor.execute('''
    SELECT priority FROM preferences
    WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    if result is not None:
        priority = result[0]
    else:
        priority = 1
    return priority


def get_total_downloads(cursor):
    cursor.execute('''
    SELECT total_downloads FROM stats
    ''')
    result = cursor.fetchone()
    if result is not None:
        total_downloads = result[0]
    else:
        total_downloads = 0
    return total_downloads


def get_total_downloads_user(cursor, user_id):
    cursor.execute('''
    SELECT downloads FROM users
    WHERE user_id = ?
    ''', (user_id,))
    total_downloads_user = cursor.fetchone()[0]
    return total_downloads_user


def get_top_downloads_user(cursor, user_id):
    cursor.execute('''
    SELECT uploader, downloads FROM downloaded_posts
    WHERE user_id = ?
    ORDER BY downloads DESC
    LIMIT 3
    ''', (user_id,))
    top_downloads_user = cursor.fetchall()
    return top_downloads_user


def update_checked_messages(cursor, user_id, message_id, max_length):
    cursor.execute('''
    SELECT id, message_id FROM checked_messages
    WHERE user_id = ?
    ORDER BY id ASC
    ''', (user_id,))
    messages = cursor.fetchall()
    cursor.execute('''
    INSERT INTO checked_messages (user_id, message_id)
    VALUES (?, ?)
    ''', (user_id, message_id))
    if len(messages) >= max_length:
        num_to_remove = len(messages) - max_length+1
        cursor.executemany('''
        DELETE FROM checked_messages WHERE id = ?
        ''', [(message[0],) for message in messages[:num_to_remove]])
    cursor.connection.commit()


def message_already_checked(cursor, user_id, message_id):
    cursor.execute('''
    SELECT 1 FROM checked_messages
    WHERE user_id = ? AND message_id = ?
    LIMIT 1
    ''', (user_id, message_id))
    return cursor.fetchone() is not None


def user_exists_check(cursor, user_id):
    cursor.execute('''
    SELECT 1 FROM users
    WHERE user_id = ?
    LIMIT 1
    ''', (user_id,))
    return cursor.fetchone() is not None


def add_user(cursor, user_id, username):
    cursor.execute('''
    INSERT INTO users (user_id, username, downloads)
    VALUES (?, ?, ?)
    ''', (user_id, username, 0))
    cursor.execute('''
    INSERT INTO preferences (user_id, priority, queue_alerts)
    VALUES (?, ?, ?)
    ''', (user_id, 1, 1))
    cursor.connection.commit()


def add_to_queue(cursor, id, user_id, user_priority, username, media_pk, media_type_int, media_type_str, author_id, media_number):
    cursor.execute('''
    INSERT OR IGNORE INTO queue (id, user_id, user_priority, username, media_pk, media_type_int, media_type_str, author_id, media_number)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (id, user_id, user_priority, username, media_pk, media_type_int, media_type_str, author_id, media_number))
    cursor.connection.commit()


def remove_queue_item(cursor, item_id):
    cursor.execute('''
    DELETE FROM queue
    WHERE id = ?
    ''', (item_id,))
    cursor.connection.commit()


def queue_is_empty(cursor):
    cursor.execute('''
    SELECT 1 FROM queue
    LIMIT 1
    ''')
    return cursor.fetchone() is None


def get_oldest_queue_item(cursor):
    cursor.execute('''
    SELECT * FROM queue
    ORDER BY user_priority DESC, id ASC
    LIMIT 1
    ''')
    return cursor.fetchone()


def get_row_count(cursor, table_name):
    cursor.execute(f'''
    SELECT COUNT(*) FROM {table_name}
    ''')
    count = cursor.fetchone()[0]
    return count


def update_user_downloads(cursor, user_id, uploader, increment):
    hash = generate_unique_id(user_id, uploader)
    cursor.execute('''
    SELECT downloads FROM downloaded_posts
    WHERE hash = ?
    ''', (hash,))
    result = cursor.fetchone()
    if result:
        cursor.execute('''
        UPDATE downloaded_posts
        SET downloads = downloads + ?
        WHERE hash = ?
        ''', (increment, hash))
    else:
        cursor.execute('''
        INSERT INTO downloaded_posts (hash, user_id, uploader, downloads)
        VALUES (?, ?, ?, ?)
        ''', (hash, user_id, uploader, increment))
    cursor.connection.commit()


def update_command_stats(cursor, command, increment):
    cursor.execute('''
    SELECT 1 FROM command_stats
    WHERE command = ?
    ''', (command,))
    result = cursor.fetchone()
    if result:
        cursor.execute('''
        UPDATE command_stats
        SET count = count + ?
        WHERE command = ?
        ''', (increment, command))
    else:
        cursor.execute('''
        INSERT INTO command_stats (command, count)
        VALUES (?, ?)
        ''', (command, increment))
    cursor.connection.commit()

def update_stats(cursor):
    cursor.execute('''
    SELECT SUM(downloads) FROM downloaded_posts
    ''')
    total_downloads = cursor.fetchone()[0] or 0
    cursor.execute('''
    SELECT COUNT(*) FROM users
    ''')
    total_users = cursor.fetchone()[0]
    cursor.execute('''
    SELECT COUNT(*) FROM stats
    ''')
    row_count = cursor.fetchone()[0]
    if row_count == 0:
        cursor.execute('''
        INSERT INTO stats (total_downloads, total_users)
        VALUES (?, ?)
        ''', (total_downloads, total_users))
    else:
        cursor.execute('''
        UPDATE stats
        SET total_downloads = ?, total_users = ?
        ''', (total_downloads, total_users))
    cursor.connection.commit()

def update_user_total_downloads(cursor, user_id):
    cursor.execute('''
    SELECT SUM(downloads) FROM downloaded_posts
    WHERE user_id = ?
    ''', (user_id,))
    total_downloads = cursor.fetchone()[0] or 0
    cursor.execute('''
    UPDATE users
    SET downloads = ?
    WHERE user_id = ?
    ''', (total_downloads, user_id))
    cursor.connection.commit()