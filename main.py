from instagrapi import Client
import sqlite3
import json
import time
import re
import os
import sys
import random
import copy
import threading
import database_functions
import json_to_database
from datetime import datetime
from pytubefix import YouTube
from pytubefix.cli import on_progress
import imageio.v3 as imageio
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip

# Get the main Instagram account username from the command line argument
system_receiver = str(sys.argv[1])

# Create the Local files folder associated with the account in case it isn't already present
os.makedirs(f'Local files/', exist_ok=True)

# Establish a connection to the database file, and create one if not present
conn = sqlite3.connect(f'Local files/{system_receiver}.db')
# Declare the 'cursor' variable for the database
cursor = conn.cursor()
# Create all the empty tables in the database if they are not already presnet
database_functions.create_tables(cursor)


path = f"Local files/{system_receiver}/database.json"

if os.path.exists(path):
    json_to_database.convert_database_from_json(cursor, path)
    os.remove(path)
    time.sleep(1)
    os.removedirs(f"Local files/{system_receiver}")
    pass

receiver_ratelimited = False
recently_ratelimited = False

def print_time(body):
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] {body}")

def print_error(body):
    error_body = f"### ERROR ### | {body}"
    print_time(error_body)

def print_error_message(e):
    print_error(f"{str(e)[0:100]}...")

def file_time():
    current_date = datetime.now().strftime('%H_%M_%S')
    return current_date

def shuffle_senders():
    global senders
    random.shuffle(senders)

def print_spacer():
    print("")

def update_bio(status):
    match status:
        case "online":
            status_string = "Online 🟢"
        case "limited":
            status_string = "Limited 🟡"
        case "offline":
            status_string = "Offline 🔴"
        case _:
            return
    new_bio = f"Status: {status_string} | made by @nikolai_nyegaard\n-\nCurrently supports: Reels, Posts, Stories, YouTube Shorts\n-"
    #receiver.account_edit(biography=new_bio)
    #print_time("Updated bio!")

def update_command_stats(command):
    # Command names: love, thank, help, downloads, contact, day
    database_functions.update_command_stats(cursor, command, 1)

def status_message(status, type, acc_from, acc_to, error="", author_id=""):
    if type.lower() != "words":
        if error == "":
            message = f"{status} | Sending {type.lower()} | From: @{acc_from} | To: @{acc_to} | Uploader: @{author_id}"
        else:
            message = f"{status} | Sending {type.lower()} | From: @{acc_from} | To: @{acc_to} | Uploader: @{author_id} | {error}"
    else:
        if error == "":
            message = f"{status} | Sending {type.lower()} | From: @{acc_from} | To: @{acc_to}"
        else:
            message = f"{status} | Sending {type.lower()} | From: @{acc_from} | To: @{acc_to} | {error}"
    return message

system_receiver = str(sys.argv[1])

testing_path = "Credentials/testing.txt"

if not os.path.exists("Credentials/"):
    os.makedirs("Credentials/", exist_ok=True)

try:
    with open (testing_path, "r") as file:
            testing = file.read().splitlines()
except:
    with open (testing_path, "w") as file:
            file.write("false")
    testing = ["false"]

try:
    with open (f"Credentials/{system_receiver}.txt", "r") as file:
        receiver_credentials = file.read().splitlines()
except Exception as e:
    print_time(f"Could not find credentials file {system_receiver}.txt")
    print_error_message(e)
    sys.exit(1)

try:
    with open (f"Credentials/senders_prod.txt", "r") as file:
        senders_prod = file.read().splitlines()
except Exception as e:
    print_time(f"Could not find credentials file senders_prod.txt")
    print_error_message(e)
    sys.exit(1)

try:
    with open (f"Credentials/senders_test.txt", "r") as file:
        senders_test = file.read().splitlines()
except Exception as e:
    print_time(f"Could not find credentials file senders_test.txt")
    print_error_message(e)
    sys.exit(1)

try:
    with open (f"Credentials/admins.txt", "r") as file:
        admins = file.read().splitlines()
except Exception as e:
    print_time(f"Could not find credentials file admins.txt")
    print_error_message(e)
    sys.exit(1)

try:
    with open (f"Credentials/owner.txt", "r") as file:
        owner_data = file.read().splitlines()
        owner_username = owner_data[0]
        owner_id = owner_data[0]
except Exception as e:
    print_time(f"Could not find credentials file owner.txt")
    print_error_message(e)
    sys.exit(1)

def wait_for_ratelimit():
    global receiver_ratelimited
    global recently_ratelimited
    receiver_ratelimited = True
    if recently_ratelimited == True:
        try:
            update_bio("limited")
        except Exception as e:
            print_error("Update bios failed.")
            print_error_message(e)
    sleep = random.randint(1200, 3600)
    print_error(f"Blocking main account text messages for {round(sleep/60)} minutes.")
    try:
        time.sleep(sleep)
    except KeyboardInterrupt:
        pass
    receiver_ratelimited = False
    recently_ratelimited = True

if len(sys.argv) != 2:
    print_time("Usage: python3 main.py <recevier_username>")
    sys.exit(1)

receiver = Client()

sender1 = Client()
sender2 = Client()
sender3 = Client()
sender4 = Client()
sender5 = Client()

sender_clients = [sender1, sender2, sender3, sender4, sender5]

if testing[0].lower() == "true":
    senders_usernames = senders_test
    senders = sender_clients[0:len(senders_usernames)]
elif testing[0].lower() == "false":
    senders_usernames = senders_prod
    senders = sender_clients[0:len(senders_usernames)]

senders_ids = []

ignored_users = []

# Get the account ID from the third line of the credentials .txt file
system_receiver_id = receiver_credentials[2]

system_sender_ids = []

for username in senders_usernames:
    with open (f"Credentials/{username}.txt", "r") as file:
        sender_credentials = file.read().splitlines()
    system_sender_ids.append(sender_credentials[2])

# Declare list of system IDs for message comparison
system_ids = system_sender_ids + [system_receiver_id]

# Message prefix to be added to the front of all messages
message_prefix = "🤖"

def sign_in_to_receiver_account():
    attempts = 0
    while attempts <= 3:
        attempts += 1
        print_time(f"Attempt {attempts} of 3 - Logging in with account {receiver_credentials[0]}...")
        try:
            mfa_code = input(f"MFA code for @{receiver_credentials[0]}: ")
            receiver.login(receiver_credentials[0],receiver_credentials[1], verification_code=mfa_code)
            #receiver.login(receiver_credentials[0],receiver_credentials[1])
            print_time("Login successful.")
            return
        except Exception as e:
            if "password" in str(e) and "incorrect" in str(e):
                print_error("Incorrect password.")
            else:
                print_error("Login failed. MFA code likely incorrect.")
                print_time(e)
                sys.exit(1)
    print_error(f"Could not log in with {receiver_credentials[0]} after {attempts} tries. Aborting.")
    sys.exit(1)

def sign_in_to_sender_accounts():
    print_time("Running 'sign_in_to_sender_accounts()")
    global senders
    updated_senders = {}
    for index, username in enumerate(senders_usernames):
        try:
            with open (f"Credentials/{username}.txt", "r") as file:
                sender_credentials = file.read().splitlines()
        except:
            print_time(f"Could not find credentials file {username}.txt")
            sys.exit(1)
        
        try:
            print_time(f"Trying to sign in with @{sender_credentials[0]}...")
            #senders[index].login(sender_credentials[0], sender_credentials[1], verification_code=input("MFA: "))
            senders[index].login(sender_credentials[0], sender_credentials[1])
            print_time(f"Login success!")
            updated_senders[index] = {
                "client": senders[index],
                "username": sender_credentials[0]
            }
        except Exception as e:
            print_error(f"Sign in with account {sender_credentials[0]} FAILED: {e}")
        
        # Check if the current iteration is the last in the series
        if index+1 == len(senders_usernames):
            time.sleep(random.randint(10,20)/10)
        else:
            seconds = random.randint(3,10)
            print_time(f"Sleeping for {seconds} seconds to stagger sign-in attempts.")
            time.sleep(seconds)
    
    senders = copy.deepcopy(updated_senders)

    if len(senders) == 0:
        print_error(f"NO senders found! See error messages. Aborting script.")
        sys.exit(1)
    else:
        print_time(f"{len(senders)} sender(s) successfully acquired.")

def log_in_again(key):
    global senders
    sender = senders[key]["client"]
    username = sender["username"]
    print_time(f"Attempting to log in again with @{username}...")
    with open (f"Credentials/{username}.txt", "r") as file:
        credentials = file.read().splitlines()
    client = sender["client"]
    try:
        client.login(credentials[0], credentials[1])
    except Exception as e:
        print_error("FAILED")
        print_error_message(e)
    senders[key]["client"] = client
        
sign_in_to_receiver_account()
sign_in_to_sender_accounts()

local_files_path = f"Local files/{system_receiver}/"

def delete_thread_as_receiver(id):
    receiver.direct_thread_hide(id)

def send_message_from_receiver(content, id, username):
    global recently_ratelimited
    if receiver_ratelimited == True:
        print_time("Receiver account ratelimited. Skipping sending message.")
        return
    username_receiver = receiver_credentials[0]
    try:
        receiver.direct_send(f"{message_prefix} {content}", user_ids=[id])
        print_time(f"{status_message("Success", "Words", username_receiver, username)} | Message: \"{content[0:40].replace("\n", " ")}...\"")
        if recently_ratelimited == True:
            recently_ratelimited == False
            try:
                update_bio("online")
            except Exception as e:
                print_error("Update bios failed.")
                print_error_message(e)
        time.sleep(random.randint(10,20)/10)
        return
    except Exception as e:
        print_error(f"There was an error sending a direct text message with @{username_receiver}.")
        if "feedback_required" in str(e):
            print_error("Receiver account is locked with a 'feedback_required' error. Halting main account text messages for some time.")
            threading.Thread(target=wait_for_ratelimit).start()
            return
        print_error_message(e)
    return

def send_message(content, id, username):
    global senders
    for index, key in enumerate(senders, start=1):
        sender = senders[key]["client"]
        username_sender = senders[key]["username"]
        try:
            sender.direct_send(f"{message_prefix} {content}", user_ids=[id])
            print_time(f"{status_message("Success", "Words", username_sender, username)} | Message: \"{content[0:40].replace("\n", " ")}...\"")
            senders = {key: senders.pop(key), **senders}
            time.sleep(random.randint(10,20)/10)
            return
        except Exception as e:
            try:
                print_error(status_message("Failure", "Words", username_sender, username, f"Error {json.loads(str(e)).get("status_code")}"))
                print_error(content)
                print_error_message(e)
            except:
                if "500 error" in str(e):
                    print_error(status_message("Failure", "Words", username_sender, username, "Error 500"))
                    return
                print_error(status_message("Failure", "Words", username_sender, username, "Unknown error"))
                print_error_message(e)
    shuffle_senders()
    return

def send_photo(content, id, username, author_id):
    global senders
    attempts = 0
    for index, key in enumerate(senders, start=1):
        sender = senders[key]["client"]
        username_sender = senders[key]["username"]
        try:
            sender.direct_send_photo(path=content, user_ids=[id])
            print_time(status_message("Success", "Photo", username_sender, username, author_id=author_id))
            senders = {key: senders.pop(key), **senders}
            time.sleep(random.randint(10,20)/10)
            return
        except Exception as e:
            try:
                print_error(status_message("Failure", "Photo", username_sender, username, error=f"Error {json.loads(str(e)).get("status_code")}", author_id=author_id))
                #print_error(f"{str(e)[0:100]}...")
                if "403" in str(e):
                    attempts += 1
                    if attempts >= 3:
                        send_message_from_receiver(f"There was a problem sending your photo from @{author_id}.\n\nTo fix this, please send a message like 'hi' to one or two of the sender accounts, and then try downloading your post again.\n\nSorry for the inconveniece!", id, username)
                        random.shuffle(senders)
                        return 403
                    print_time("Retrying with new sender...")
            except:
                if "500 error" in str(e):
                    print_error(status_message("Failure", "Photo", username_sender, username, "Error 500", author_id=author_id))
                    return
                print_error(status_message("Failure", "Photo", username_sender, username, "Unknown error", author_id=author_id))
                print_error_message(e)
    shuffle_senders()
    return

def send_video(content, id, username, author_id):
    global senders
    attempts = 0
    for index, key in enumerate(senders, start=1):
        sender = senders[key]["client"]
        username_sender = senders[key]["username"]
        try:
            sender.direct_send_video(path=content, user_ids=[id])
            print_time(status_message("Success", "Video", username_sender, username, author_id=author_id))
            senders = {key: senders.pop(key), **senders}
            time.sleep(random.randint(10,20)/10)
            return
        except Exception as e:
            try:
                print_error(status_message("Failure", "Video", username_sender, username, error=f"Error {json.loads(str(e)).get("status_code")}", author_id=author_id))
                #print_error(f"{str(e)[0:100]}...")
                if "403" in str(e):
                    attempts += 1
                    if attempts >= 3:
                        send_message_from_receiver(f"There was a problem sending your video from @{author_id}.\n\nTo fix this, please send a message like 'hi' to one or two of the sender accounts, and then try downloading your post again.\n\nSorry for the inconveniece!", id, username)
                        random.shuffle(senders)
                        return 403
                    print_time("Retrying with new sender...")
            except:
                if "500 error" in str(e):
                    print_error(status_message("Failure", "Video", username_sender, username, "Error 500", author_id=author_id))
                    return
                elif "login_required" in str(e):
                    print_error(status_message("Failure", "Video", username_sender, username, "'login_required'", author_id=author_id))
                    log_in_again(key)
                print_error(status_message("Failure", "Video", username_sender, username, "Unknown error", author_id=author_id))
                print_error_message(e)
    shuffle_senders()
    return


# Automated messages
def my_downloads(total, top, name):
    header = f"Hello {name}!\n\n"
    body1 = f"Your total downloads: {total}\n\n"
    body2 = f"Your top accounts:\n"
    body3 = ""
    for index, (uploader, downloads) in enumerate(top, start=1):
        body3 += f"{index}. {downloads} | @{uploader}\n"
    body3 += "\n"
    footer = "Happy downloading!"
    message = header + body1 + body2 + body3 + footer
    return message

def help_message(name):
    message = f"Hello {name}!\n\nHere is the help menu:\n• !help donate\n• !help priority\n• !help commands\n• !help general\n• !help reels\n• !help posts\n• !help stories\n• !help contact"
    return message

def help_commands_message(name):
    message = f"Hello {name}!\n\nHere is the list of commands:\n• !downloads - Shows your total downloads and a list of the top 3 uploaders you've downloaded from.\n• !contact <message> - Sends a message to the admin, for things like questions or reporting issues.\n• !day - Shows statistics for today, like the number of downloads, users, and new users."
    return message

def help_donations_message(name):
    message = f"Hello {name}!\n\nIf you want to support me and the development of the service, you can choose to donate a few dollars to me through the Ko-fi link in my bio, or shout out the service on your story on a public account.\n\nIf you donate or give me a shoutout, you also receive benefits!\n\nTo receive benefits, you have to contact me to let me know you've donated or shouted me out using the !contact command. Type '!help contact' for more info.\n\nBenefits include an increased priority level in the queue, and an increased 'message search depth' when sending things to the bot.\n\nTo learn more about priority and search depth, type '!help priority'."
    return message

def help_priority_message(name):
    message = f"Hello {name}!\n\nFor each $3 donated or story shouout done, you will receive 1 additional level of priority.\n\nPriority is a value associated with each user of the service. Whenever the queue is handled, it is sorted so that users with the highest priority gets their posts first, and don't have to wait for the queue to finish.\n\nMesage search depth is a value which determines how many messages in the conversation the bot will look at and download.\n\nBy default, tihs value is 2, meaning if you send the bot 5 posts in a row, it will only look at and download the last 2 posts. This value increases +1 for each level of priority, so if you have priority level 4, it will look at the last 5 posts in the conversation."
    return message

def help_posts_message(name):
    message = f"Hello {name}!\n\nTo download posts, simply send the post to the bot using the send button.\n\nThe bot works with both single photo, single video, and album posts.\n\nIf the post is from a private page, it won't work unless I follow them.\n\nIf you want me to follow someone, type '!contact Can you follow @accountname?' and I'll send them a request."
    return message

def help_reels_message(name):
    message = f"Hello {name}!\n\nTo download reels, simply send the reel to the bot using the send button.\n\nOccasionally, Instagram will prevent this from working due to some unknown reason, and when that happens, you can send the link to the reel instead. The link will always work, but sending it normally is faster and easier.\n\nIf the reel is from a private account, it won't work unless I follow them.\n\nIf you want me to follow someone, type '!contact Can you follow @accountname?' and I'll send them a request."
    return message

def help_stories_message(name):
    message = f"Hello {name}!\n\nTo download reels, simply send the story to the bot using the send button.\n\nSometimes, stories don't have the send button if the creator has changed their settings to not allow it. In this case, you can't download the story, unfortunately.\n\nIf the story is from a private account, it won't work unless I follow them.\n\nIf you want me to follow someone, type '!contact Can you follow @accountname?' and I'll send them a request."
    return message

def help_contact_message(name):
    message = f"Hello {name}!\n\nYou can use the !contact command to send a message directly to the admin.\n\nTo do this, simply type '!contact' followed by whatever you want to say.\n\nHere is an example:\n\n!contact Hey, I have some questions about the bot. Can you message me back?"
    return message

def help_general_message(name):
    message = f"Hello {name}!\n\nThis is a downloader bot which you can use to convert an Instagram post into a video or photo you can save to your phone.\n\nTo do this, simply send the reel, post, or story to the bot, and after a couple minutes, you'll get sent a photo or video from one of the sender-bots.\n\nWe also support YouTube Shorts and YouTube videos, which you can download by copying the link for the YouTube video and sending it to the bot."
    return message

def welcome_message(name):
    if name == "":
        name_string = ""
    else:
        name_string = f" {name}"

    match random.randint(1,3):
        case 1:
            header = f"Greetings{name_string}!\n\n"
        case 2:
            header = f"Welcome{name_string}!\n\n"
        case 3:
            header = f"Salutations{name_string}!\n\n"

    match random.randint(1,3):
        case 1:
            body1 = f"You can type '!help' for more info or type '!contact <message>' to send a message to the admin.\n\n"
        case 2:
            body1 = f"Feel free to use the !help command to get some more info, or send me a message by typing !contact followed by what you want to say, like \"!contact Hello!\"\n\n"
        case 3:
            body1 = f"If you want more information, type !help, and if you want to reach out to me, type !contact followed by your message.\n\n"

    match random.randint(1,3):
        case 1:
            body2 = f"Sometimes when you use the bot for the first time, your downloaded pictures and videos don't get delivered by the sender bots. This can be because your message settigns blocks accounts you don't follow from messaging you. If this happens, please try sending a message to one or two of the sender accounts, which can be found in the queue message, and try downloading your post again.\n\n"
        case 2:
            body2 = f"If it's your first time using the bot and you notice you didn't receive your downloaded photos or videos, it can be because your message settings stops the sender bots from messaging you. To fix this, send a message like 'Hi' to one or two of the sender accounts (found in the queue message), and try downloading the post again.\n\n"
        case 3:
            body2 = f"If you've tried downloading a post but noticed that you didn't get your downloaded photos or videos, it can sometimes be because your message settings doesn't allow messages from accounts you don't follow. To fix this, please send a message, like 'Hello', to one or two of the sender bots (you can find them in the queue message). Then, try to download the post again.\n\n"

    match random.randint(1,3):
        case 1:
            footer = f"Thank you for using the service, and happy downloading!"
        case 2:
            footer = f"Thanks for reading, and happy downloading!"
        case 3:
            footer = f"Thank you, happy downloading, and have a nice day!"
    
    message = header + body1 + body2 + footer

    # Return the message
    return message


def i_love_you(name):
    # Select a random number between 1 and 4
    message_selector = random.randint(1,4)
    # Pick a message based on the random number
    match name:
        case "":
            match message_selector:
                case 1:
                    message = "I love you too!"
                case 2:
                    message = "Aww, I love you too"
                case 3:
                    message = "R-really? I love you too.."
                case 4:
                    message = "You're just saying that..."
        case _:
            match message_selector:
                case 1:
                    message = f"I love you too, {name}!"
                case 2:
                    message = f"Aww, I love you too, {name}"
                case 3:
                    message = f"R-really? I love you too, {name}..."
                case 4:
                    message = f"You're just saying that, {name}..."

    return message


def thanks(name):
    # Select a random number between 1 and 4
    message_selector = random.randint(1,3)
    # Pick a message based on the random number
    match name:
        case "":
            match message_selector:
                case 1:
                    message = "No problem!"
                case 2:
                    message = "You're welcome!"
                case 3:
                    message = "It was my pleasure!"
        case _:
            match message_selector:
                case 1:
                    message = f"No problem, {name}!"
                case 2:
                    message = f"You're welcome, {name}!"
                case 3:
                    message = f"It was my pleasure, {name}!"

    return message


def placeholder_error_message():
    message = "The last message you sent encountered an error.\n\nThis might be because the post is private or the uploader has blocked me.\n\n⚠️ If it was a Reel, please try sending a link instead. This is normally not necessary, but can be a workaround when normal Reels fail."
    return message


def queue_length_message(queue_length):
    message = f"There are {queue_length} items in the queue."
    return message


def added_x_to_queue_message(items_list):
    total = 0
    for item in items_list:
        total += item[0]
    if total == 1:
        match random.randint(1,2):
            case 1:
                header = f"Added {total} item to queue:\n\n"
            case 2:
                header = f"Placed {total} item in the queue:\n\n"
    elif total > 1:
        match random.randint(1,2):
            case 1:
                header = f"Added {total} items to queue:\n\n"
            case 2:
                header = f"Placed {total} items in the queue:\n\n"
        header = f"Added {total} items to queue:\n\n"
    else:
        header = ""
    body = ""
    for item in items_list:
        quantity = item[0]
        type = item[1]
        author = item[2]
        if type != "YouTube video":
            if quantity == 1:
                string = f"• {quantity} {type} from @{author}\n"
            elif quantity > 1:
                string = f"• {quantity} items from @{author}\n"
        else:
            string = f"• {quantity} video from {author}\n"

        body += string
    if len(senders_usernames) == 1:
        accounts_plural = "the sender account"
    else:
        accounts_plural = "one or two of the sender accounts"
    footer = f"\n\nYou will receive the downloaded media from a different account.\n\n⚠️ If you get an error saying your media couldn't be delivered, it's because the senders were blocked from messaging you. To fix this, send message like 'hi' to {accounts_plural} below. Otherwise, they will not be able to send you your downloaded media:"
    footer_accounts = ""
    for account in senders_usernames:
        footer_accounts += f"\n• @{account}"
    message = header+body+footer+footer_accounts
    return message

def parse_user(user_string):
    user_data = {}
    # Regular expression to match key-value pairs
    pattern = re.compile(r"(\w+)='([^']*)'|(\w+)=([^ ]*)")
    matches = pattern.findall(user_string)
    for match in matches:
        key = match[0] or match[2]
        value = match[1] or match[3]
        if value.startswith("Url(") and value.endswith(")"):
            value = value[4:-1]
        user_data[key] = value
    return user_data

def get_inbox():
    threads = []
    pending_threads = []
    inbox_threads = []
    print_time("Fetching inbox threads...")
    try:
        receiver.direct_threads(selected_filter="unread")
        #receiver.direct_threads(amount=20)
        time.sleep(random.randint(10,20)/10)
    except:
        pass
    last_json_inbox = receiver.last_json
    try:
        inbox_threads = last_json_inbox["inbox"]["threads"]#[0:20]
        print_time(f"Fetched {len(inbox_threads)} new inbox threads!")
    except Exception as e:
        return False
    try:
        if len(inbox_threads) == 0:
            return inbox_threads
    except:
        pass
    print_time("Fetching pending threads...")
    try:
        receiver.direct_pending_inbox(amount=20)
        time.sleep(random.randint(10,20)/10)
    except:
        pass
    last_json_pending = receiver.last_json
    pending_threads = last_json_pending["inbox"]["threads"]
    print_time(f"Fetched {len(pending_threads)} new pending threads!")

    threads = pending_threads + inbox_threads
    return threads


def convert_heic_and_send(media_path, directory, filename):
    try:
        jpeg_path = os.path.join(directory, "".join(filename) + ".jpg")
        image = imageio.imread(media_path)
        image = Image.fromarray(np.uint8(image))
        image.save(jpeg_path, "JPEG")
        os.remove(media_path)
        return jpeg_path
    except Exception as e:
        print_error(f"An error occurred: {e}")
        raise

# Function for downloading the images and videos of an album
def download_album(post_pk, user_id, directory, username, author_id):
    # Download the media to the path
    try:
        receiver.album_download(media_pk=post_pk, folder=directory)
        #print_time(f"Successfully downloaded album with @{receiver_credentials[0]}")
    except:
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                sender.album_download(media_pk=post_pk, folder=directory)
                #print_time(f"Successfully downloaded album with @{username_sender}")
                break
            except Exception as e:
                print_error(f"Photo download failed with @{username_sender}.")
                #print_error_message(e)
                print_error(f"Retrying with next sender...")
    # Loop over media in folder to send to the user
    files = os.listdir(directory)
    status = 0
    for index, filename in enumerate(files, start=1):
        media_path = os.path.join(directory, filename)
        print_time(f"Sending file {index} of {len(files)}")
        match filename.split('.')[-1]:
            case "jpg" | "jpeg" | "png"  | "webp":
                status = send_photo(media_path, user_id, username, author_id)
            case "mp4":
                status = send_video(media_path, user_id, username, author_id)
            case "heif" | "heic":
                try:
                    media_path = convert_heic_and_send(media_path, directory, filename.split('.')[0:-1])
                except Exception as e:
                    print_error(f"convert_heic_and_send() failed with file {filename}")
                    print_error_message(e)
                    continue
                status = send_photo(media_path, user_id, username, author_id)
            case _:
                print_time("Failed to find appropriate media type")
                continue
        if status == 403:
            return 403

# Function for downloading single videos, like Reels
def download_video(post_pk, user_id, directory, username, author_id):
    # Download the media to the path
    try:
        # receiver.clip_download(media_pk=post_pk, folder=directory)
        # print_time(f"Successfully downloaded album with @{receiver_credentials[0]}")
        raise KeyError #Temporary to avoid rewrite
    except:
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                sender.clip_download(media_pk=post_pk, folder=directory)
                #print_time(f"Successfully downloaded video with @{username_sender}")
                time.sleep(random.randint(10,20)/10)
                break
            except Exception as e:
                print_error(f"Video download failed with @{username_sender}.")
                #print_error_message(e)
                print_error(f"Retrying with next sender...")
    status = 0
    # Loop over media in folder to send to the user
    for filename in os.listdir(directory):
        media_path = os.path.join(directory, filename)
        match filename.split('.')[-1]:
            case "mp4" | "hevc" | "mov" | "m4v":
                status = send_video(media_path, user_id, username, author_id)
            case _:
                print_error(f"Video file ({filename[-4:]}) did not match the .mp4 format!")
                continue
        if status == 403:
            return 403

# Function for downloading single videos, like Reels
def download_story(post_pk, user_id, directory, username, author_id):
    # Download the media to the path
    try:
        receiver.story_download(story_pk=post_pk, folder=directory)
        # print_time(f"Successfully downloaded album with @{receiver_credentials[0]}")
    except:
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                sender.story_download(story_pk=post_pk, folder=directory)
                # print_time(f"Successfully downloaded story with @{username_sender}")
                time.sleep(random.randint(10,20)/10)
                break
            except Exception as e:
                print_error(f"Story download failed with @{username_sender}.")
                print_error_message(e)
                print_error(f"Retrying with next sender...")
    status = 0
    # Loop over media in folder to send to the user
    for filename in os.listdir(directory):
        media_path = os.path.join(directory, filename)
        match filename.split('.')[-1]:
            case "mp4" | "hevc" | "mov" | "m4v":
                status = send_video(media_path, user_id, username, author_id)
            case "jpg" | "jpeg" | "png"  | "webp":
                status = send_photo(media_path, user_id, username, author_id)
            case _:
                print_error(f"Video file ({filename[-4:]}) did not match the .mp4 format!")
                continue
        if status == 403:
            return 403

# Function for downloading single photos, like posts
def download_photo(post_pk, user_id, directory, username, author_id):
    # Download the media to the path
    try:
        # receiver.photo_download(media_pk=post_pk, folder=directory)
        # print_time(f"Successfully downloaded album with @{receiver_credentials[0]}")
        raise KeyError
    except:
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                sender.photo_download(media_pk=post_pk, folder=directory)
                #print_time(f"Successfully downloaded photo with @{username_sender}")
                break
            except Exception as e:
                print_error(f"Problems downloading photo using sender @{username_sender}.")
                #print_error_message(e)
                print_error(f"Retrying with next sender...")
    status = 0
    # Loop over media in folder to send to the user
    for filename in os.listdir(directory):
        media_path = os.path.join(directory, filename)
        match filename.split('.')[-1]:
            case "jpg" | "jpeg" | "png"  | "webp":
                send_photo(media_path, user_id, username, author_id)
            case "heif" | "heic":
                try:
                    media_path = convert_heic_and_send(media_path, directory, filename.split('.')[0:-1])
                except Exception as e:
                    print_error(f"convert_heic_and_send() failed with file {filename}")
                    print_error_message(e)
                    continue
                send_photo(media_path, user_id, username, author_id)
            case _:
                continue
        if status == 403:
            return 403


def download_youtube(url, user_id, directory, username, identifier, author_id):
    try:
        priority = database_functions.get_priority(cursor, user_id)
    except Exception as e:
        print_error(f"Problems getting the user priority from the database")
        return
    youtube_item = YouTube(url, on_progress_callback = on_progress)
    print_time(f"Downloading YouTube video for @{username}...")
    if priority > 2:
        try:
            highest_res_video = youtube_item.streams.filter(adaptive=True, only_video=True, mime_type="video/mp4").order_by('resolution').desc().first()
            video_temp_name = f"{identifier}_temp.mp4"
            highest_res_video.download(output_path=directory, filename=video_temp_name)
            path = os.path.join(directory, video_temp_name)
            if not os.path.exists(path):
                raise FileNotFoundError
        except:
            try:
                highest_res_video = youtube_item.streams.filter(adaptive=True, only_video=True, mime_type="video/webm").order_by('resolution').desc().first()
                video_temp_name = f"{identifier}_temp.webm"
                highest_res_video.download(output_path=directory, filename=video_temp_name)
                path = os.path.join(directory, video_temp_name)
                if not os.path.exists(path):
                    raise FileNotFoundError
            except Exception as e:
                print_error_message(e)
                return
    else:
        try:
            highest_res_video = youtube_item.streams.filter(adaptive=True, only_video=True, mime_type="video/mp4", res="480p").order_by('resolution').desc().first()
            video_temp_name = f"{identifier}_temp.mp4"
            highest_res_video.download(output_path=directory, filename=video_temp_name)
            path = os.path.join(directory, video_temp_name)
            if not os.path.exists(path):
                raise FileNotFoundError
        except:
            try:
                highest_res_video = youtube_item.streams.filter(adaptive=True, only_video=True, mime_type="video/webm", res="480p").order_by('resolution').desc().first()
                video_temp_name = f"{identifier}_temp.webm"
                highest_res_video.download(output_path=directory, filename=video_temp_name)
                path = os.path.join(directory, video_temp_name)
                if not os.path.exists(path):
                    raise FileNotFoundError
            except:
                print_error_message(e)
                return
    try:
        highest_quality_audio = youtube_item.streams.filter(only_audio=True, mime_type="audio/webm").order_by('abr').desc().first()
        audio_temp_name = f"{identifier}_temp.webm"
        highest_quality_audio.download(output_path=directory, filename=audio_temp_name)
        path = os.path.join(directory, audio_temp_name)
        if not os.path.exists(path):
            raise FileNotFoundError
    except:
        try:
            highest_quality_audio = youtube_item.streams.filter(only_audio=True, mime_type="audio/mp4").order_by('abr').desc().first()
            audio_temp_name = f"{identifier}_temp.mp4"
            highest_quality_audio.download(output_path=directory, filename=audio_temp_name)
            path = os.path.join(directory, audio_temp_name)
            if not os.path.exists(path):
                raise FileNotFoundError
        except Exception as e:
            print_error_message(e)
            return

    video_file = VideoFileClip(f"{directory}/{video_temp_name}")
    audio_file = AudioFileClip(f"{directory}/{audio_temp_name}")
    if video_file.duration is None or audio_file.duration is None:
        print_error("Failed to load audio or video file correctly.")
        return
    try:
        video_with_audio = video_file.set_audio(audio_file)
        if video_with_audio.audio is None:
            print_error("Audio not set correctly.")
            return
        filename = f"{identifier}.mp4"
        try:
            video_with_audio.write_videofile(f"{directory}/{filename}", codec="libx264", audio_codec="aac")
        except Exception as e:
            print_error(f"Error during complex write_videofile: {e}")
            try:
                video_with_audio.write_videofile(f"{directory}/{filename}")
            except Exception as e:
                print_error(f"Error during simple write_videofile: {e}")
                return
            try:
                os.remove(f"{directory}/{video_temp_name}")
                os.remove(f"{directory}/{audio_temp_name}")
            except Exception as e:
                print_error("Failed to delete temp files in download_youtube()")
                print_error_message(e)
                return
    except Exception as e:
        print_error("Failed to attach audio file to video in download_youtube()")
        print_error_message(e)
        return

    try:
        send_video(f"{directory}/{filename}", user_id, username, author_id)
    except Exception as e:
        print_error("send_video() inside download_youtube() failed")
        print_error_message(e)
        return
    

def determine_post_type(media_info):
    match media_info.media_type, media_info.product_type:
        case 1, _:
            return "photo", 1
        case 2, "story":
            return "story", 1
        case 2, _:
            return "video", 1
        case 8, _:
            return "album", len(media_info.resources)
        case _:
            return "error", 0


def handle_media_share(message, user_id, username, priority):
    try:
        post_url = message["xma_media_share"][0]["target_url"].split("?")[0]
    except:
        return False, False, False, False, False, None
    for index, key in enumerate(senders, start=1):
        sender = senders[key]["client"]
        username_sender = senders[key]["username"]
        try:
            post_pk = sender.media_pk_from_url(post_url)
            media_info = sender.media_info(post_pk)
            author_id = media_info.model_dump()["user"]["username"]
            media_type_str, media_number = determine_post_type(media_info)
            media_type_int = media_info.media_type
            #add_to_queue(cursor, user_id, user_priority, username, media_pk, media_type_int, media_type_str, author_id, media_number)
            return media_type_str, media_type_int, post_pk, author_id, media_number, None
        except Exception as e:
            if "Media not found or unavailable" in str(e):
                print_error(f"handle_media_share() - FAILED with sender {username_sender}")
                print_error_message(e)
                send_message_from_receiver("One of the posts you sent appears to have been deleted or removed.", user_id, username)
                return False, False, False, False, False, None
            print_error(f"handle_media_share() - FAILED with sender {username_sender}")
            print_error_message(e)
    return False, False, False, False, False, None


def handle_reel(message, user_id, username, priority):
    try:
        post_pk = str(message["clip"]).split(" ")[0].split("=")[1]
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                media_info = sender.media_info(post_pk)
                author_id = media_info.model_dump()["user"]["username"]
                media_type_str, media_number = determine_post_type(media_info)
                media_type_int = media_info.media_type
                return media_type_str, media_type_int, post_pk, author_id, media_number, None
            except:
                try:
                    print_error(f"handle_reel() - Problems getting Reel media info with sender {username_sender}")
                    print_error_message(e)
                    continue
                except:
                    pass
    except Exception as e:
        print_error(f"handle_reel() failed with {e}")
    return False, False, False, False, False, None

def prepare_youtube_element_for_queue(url, user_id, username, priority):
    url = url.split("?")[0]
    identifier = url.split("/")[-1]
    youtube_item = YouTube(url, on_progress_callback = on_progress)
    author_id = youtube_item.author
    media_number = 1
    post_pk = url
    media_type_str = "YouTube video"
    media_type_int = 3
    # key = f"{user_id}_{identifier}"
    # queue_item = {
    #     "user_id": user_id,
    #     "user_priority": priority,
    #     "username": username,
    #     "media_pk": url,
    #     "media_type_int": 3,
    #     "media_type_str": "YouTube video",
    #     "author_id": author,
    #     "media_number": 1,
    #     "youtube_id": identifier
    #     }
    return media_type_str, media_type_int, post_pk, author_id, media_number, identifier
    
def handle_link(message, user_id, username, priority):
    try:
        url = message["link"]["text"]
    except:
        url = message["xma_link"][0]["target_url"]
    
    if "instagram.com/reel/" in url:
        post_pk = False
        for index, key in enumerate(senders, start=1):
            sender = senders[key]["client"]
            username_sender = senders[key]["username"]
            try:
                post_pk = sender.media_pk_from_url(url)
                media_info = sender.media_info(post_pk)
                author_id = media_info.model_dump()["user"]["username"]
                media_type_str, media_number = determine_post_type(media_info)
                media_type_int = media_info.media_type
                return media_type_str, media_type_int, post_pk, author_id, media_number, None
            except Exception as e:
                if "Media not found or unavailable" in str(e):
                    print_error_message(e)
                    send_message_from_receiver("One of the links you sent appears to have been deleted or removed.", user_id, username)
                    return False, False, False, False, False, None
                else:
                    print_error(f"handle_link() - FAILED with sender {username_sender}")
                    print_error_message(e)
        send_message_from_receiver("There was a problem with your link. Try sending the Reel normally.", user_id, username)
        return False, False, False, False, False, None
    elif "instagram.com/stories/" in url:
        send_message_from_receiver("Downloading stories via links is currently not supported. You can use links for Reels or YouTube Shorts or YouTube videos.", user_id, username)
    elif "youtube.com" in url or "yt.be" in url or "youtu.be" in url:
        try:
            media_type_str, media_type_int, post_pk, author_id, media_number, youtube_id = prepare_youtube_element_for_queue(url, user_id, username, priority)
            return media_type_str, media_type_int, post_pk, author_id, media_number, youtube_id
        except Exception as e:
            send_message_from_receiver("There was a problem with your link. Try a different video or try again later.", user_id, username)
            print_error_message(e)

    return False, False, False, False, False, None


def handle_story(message, user_id, username, priority):
    try:
        post_url = message["xma_story_share"][0]["target_url"].split("?")[0]
    except:
        return False, False, False, False, False, None
    for index, key in enumerate(senders, start=1):
        sender = senders[key]["client"]
        username_sender = senders[key]["username"]
        try:
            post_pk = sender.story_pk_from_url(post_url)
            media_info = sender.story_info(post_pk)
            author_id = media_info.model_dump()["user"]["username"]
            media_type_str, media_number = determine_post_type(media_info)
            media_type_int = media_info.media_type
            return media_type_str, media_type_int, post_pk, author_id, media_number, None, None
        except:
            print_error(f"handle_story() - Get media_info from post_pk FAILED with sender {username_sender}")
            return False, False, False, False, False, None


def handle_love(user_id, name, username):
    response = i_love_you(name)
    update_command_stats("love")
    send_message_from_receiver(response, user_id, username)

def handle_thanks(user_id, name, username):
    response = thanks(name)
    update_command_stats("thanks")
    send_message_from_receiver(response, user_id, username)

def handle_downloads_command(user_id, name, username):
    total_downloads = database_functions.get_total_downloads_user(cursor, user_id)
    top_downloads = database_functions.get_top_downloads_user(cursor, user_id)
    update_command_stats("downloads")
    send_message_from_receiver(my_downloads(total_downloads, top_downloads, name), user_id, username)

def handle_downloaded_command(user_id, name, username, content):
    content_split = content.split(" ")
    if len(content_split) != 2:
        send_message_from_receiver(f"Invalid format: {content}\n\n'Downloaded' commands should be formatted as '!downloaded <username or \"me\">'.", user_id, username)
    uploader = content_split.strip("@")

def handle_help_command(user_id, name, arguments, content, username):
    update_command_stats("help")
    match len(arguments):
        case 1:
            send_message_from_receiver(help_message(name), user_id, username)
        case 2:
            match arguments[1]:
                case "commands":
                    send_message_from_receiver(help_commands_message(name), user_id, username)
                case "posts":
                    send_message_from_receiver(help_posts_message(name), user_id, username)
                case "reels":
                    send_message_from_receiver(help_reels_message(name), user_id, username)
                case "stories":
                    send_message_from_receiver(help_stories_message(name), user_id, username)
                case "contact":
                    send_message_from_receiver(help_contact_message(name), user_id, username)
                case "general":
                    send_message_from_receiver(help_general_message(name), user_id, username)
                case _:
                    pass
        case _:
            send_message_from_receiver(f"Invalid format: {content}\n\nHelp commands should be formatted as '!help <argument>'.", user_id, username)

def handle_contact_command(id, username, content, content_unedited):
    extracted_message = content_unedited.removeprefix("!contact ")
    messageToAdmin = f"You have a new message!\n\nFrom @{username}:\n\n{extracted_message}"
    messageToUser = f"Mesasge sent to @{owner_username}:\n\n{extracted_message}"
    update_command_stats("contact")
    send_message_from_receiver(messageToAdmin, owner_id, owner_username)
    time.sleep(random.randint(5,15)/10)
    send_message_from_receiver(messageToUser, id, username)
    
def handle_day_command(id, name, username):
    update_command_stats("day")
    send_message_from_receiver("The !day command currently doesn't work :-(", id, username)
    pass

def handle_unknown_command(id, name, username, content):
    message =f"Unknown command: {content}"
    send_message_from_receiver(message, id, username)

def handle_commands(content, content_unedited, user_id, name, username):
    arguments = content.split(" ")
    command = arguments[0]
    match command:
        case "!help":
            handle_help_command(user_id, name, arguments, content, username)
        case "!downloads":
            handle_downloads_command(user_id, name, username)
        case "!downloaded":
            handle_downloaded_command(user_id, name, username, content)
        case "!contact":
            handle_contact_command(user_id, username, content, content_unedited)
        case "!day":
            handle_day_command(user_id, name, username)
        case _:
            handle_unknown_command(user_id, name, username, content)


def handle_text(message, user_id, name, username):
    content_unedited = message["text"]
    content = content_unedited.lower()
    if content[0] == "!":
        handle_commands(content, content_unedited, user_id, name, username)
    elif "love you" in content or "luv you" in content or "love u" in content or "luv u" in content:
        handle_love(user_id, name, username)
    elif "thank" in content or "thx" in content or "cheers" in content or "goat" in content or "the best" in content:
        handle_thanks(user_id, name, username)


# Handle the messages fetched from the inbox
def handle_threads(threads):
    total_threads = len(threads)

    # Loop through all threads in inbox
    for index, thread in enumerate(threads, start=1):

        # Declare thread variables
        try:
            user = thread["users"][0]
        except:
            try:
                delete_thread_as_receiver(thread["thread_id"])
            except:
                continue
            continue
        all_messages = thread["items"]
        user_messages = [item for item in all_messages if item["user_id"] not in system_ids]

        # Check the variable type of the 'user' object
        if type(user) != dict:
            user = parse_user(str(user))
        
        # Declare user detail variables
        username = user["username"]
        user_id = user["pk"]
        name = user["full_name"]

        # Update the total number of downloads for the user in the database
        database_functions.update_user_total_downloads(cursor, user_id)

        if not name.isupper():
            name = name.title()

        num_of_items_added_to_queue = 0
        
        print_spacer()
        print_time(f"Handling thread {index} of {total_threads} for user @{username}")
        
        # If the user's name is "Instragram User", they are a banned account and handling their messages is a waste of time.
        comparison_name = "Instagram User"
        deleted_indicator = "__deleted__"
        if username == comparison_name or deleted_indicator in username:
            print_time(f"Deleting thread for @{username}")
            delete_thread_as_receiver(thread["thread_id"])
            continue
        try:
            message_text = all_messages[0]["text"]
        except:
            message_text = False
            pass

        if all_messages[0]["user_id"] != user_id:
            if not message_text == False:
                if "We have temporarily" in message_text:
                    pass
                else:
                    print_time("Last message in thread is from the bot. Skipping thread.")
                    delete_thread_as_receiver(thread["thread_id"])
                    continue
            else:
                print_time("Last message in thread is from the bot. Skipping thread.")
                delete_thread_as_receiver(thread["thread_id"])
                continue

        # If the user's name is in the 'ignored_users' list, continue to the next thread without processing the messages
        if username in ignored_users:
            delete_thread_as_receiver(thread["thread_id"])
            continue

        # Check if the user is a new user
        if database_functions.user_exists_check(cursor, user_id):
            new_user = False
        else:
            send_message_from_receiver(welcome_message(name), user_id, username)
            new_user = True
            database_functions.add_user(cursor, user_id, username)
        
        priority = database_functions.get_priority(cursor, user_id)

        # Hard coded "priority" function. Remove later for more refined function.
        message_depth = priority+1
        
        # Declare some variables
        total_messages = len(user_messages[0:message_depth])
        items_added_to_queue = []

        # Loop through all messages in thread
        for index, message in enumerate(user_messages[0:message_depth], start=1):
            print_time(f"Handling message {index} of {total_messages}")
            message_id = message["item_id"]

            youtube_id = None
            post_pk = False
            media_number = 0

            # If the user does not exist in the database file, skip the message ID check
            if new_user == True:
                pass
            else:
                # If the message exists in the checked_messages array of the user, skip the rest of the thread
                if database_functions.message_already_checked(cursor, user_id, message_id):
                    break

            # If the message does not exist in the checked_messages array, run the function to add it and update the database
            database_functions.update_checked_messages(cursor, user_id, message_id, max_length=15)

            message_type = message["item_type"]
            # print(message_type)
            match message_type, index:
                case "xma_media_share", _:
                    media_type_str, media_type_int, post_pk, author_id, media_number, _ = handle_media_share(message, user_id, username, priority)
                case "clip", _:
                    media_type_str, media_type_int, post_pk, author_id, media_number, _ = handle_reel(message, user_id, username, priority)
                case "link", _:
                    #send_message_from_receiver("Links are broken right now, but I'll be fixing it tomorrow. Sorry for the inconvenience!", user_id, username)
                    media_type_str, media_type_int, post_pk, author_id, media_number, _ = handle_link(message, user_id, username, priority)
                case "xma_link", _:
                    #send_message_from_receiver("Links are broken right now, but I'll be fixing it tomorrow. Sorry for the inconvenience!", user_id, username)
                    media_type_str, media_type_int, post_pk, author_id, media_number, youtube_id = handle_link(message, user_id, username, priority)
                case "xma_story_share", _:
                    media_type_str, media_type_int, post_pk, author_id, media_number, _ = handle_story(message, user_id, username, priority)
                case "xma_profile", _:
                    continue
                case "text", _:
                    handle_text(message, user_id, name, username)
                case "placeholder", 1:
                    send_message_from_receiver(placeholder_error_message(), user_id, username)
                    continue
                case _:
                    continue
            
            if not post_pk:
                continue

            id = database_functions.generate_unique_id(user_id, post_pk)

            if media_number != 0:
                database_functions.add_to_queue(cursor, id, user_id, priority, username, post_pk, media_type_int, media_type_str, author_id, media_number, youtube_id)
                items_added_to_queue.append((media_number, media_type_str, author_id))
                match media_number:
                    case 1:
                        items_plural = "item"
                    case _:
                        items_plural = "items"
                print_time(f"Added {media_number} {items_plural} to the queue!")
                num_of_items_added_to_queue += media_number
            else:
                continue
        
        if num_of_items_added_to_queue == 0:
            delete_thread_as_receiver(thread["thread_id"])
            continue

        send_message_from_receiver(added_x_to_queue_message(items_added_to_queue), user_id, username)
        time.sleep(random.randint(10,20)/10)

        if username not in admins:
            delete_thread_as_receiver(thread["thread_id"])


def handle_queue():
    # Get the details of the next item in the queue
    id, user_id, _, username, media_pk, media_type_int, media_type_str, author, media_number, youtube_id = database_functions.get_oldest_queue_item(cursor)
    
    queue_count = database_functions.get_row_count(cursor, 'queue')
    print_time(f"Current queue: {queue_count}")

    if not youtube_id is None:
        directory = os.path.join(os.getcwd(), f"Temp/{user_id}/{author}/{youtube_id}")
        os.makedirs(directory, exist_ok=True)
    else:
        directory = os.path.join(os.getcwd(), f"Temp/{user_id}/{author}/{media_pk}")
        os.makedirs(directory, exist_ok=True)

        status = 0

    try:
        if media_type_int == 8:
            try:
                status = download_album(media_pk, user_id, directory, username, author)
            except Exception as e:
                print_error(f"download_album() in handle_queue() failed with: {e}")
        elif media_type_str == "story":
            try:
                status = download_story(media_pk, user_id, directory, username, author)
            except Exception as e:
                print_error(f"download_story() in handle_queue() failed with: {e}")
        elif media_type_int == 2:
            try:
                status = download_video(media_pk, user_id, directory, username, author)
            except Exception as e:
                print_error(f"download_video() in handle_queue() failed with: {e}")
        elif media_type_int == 1:
            try:
                status = download_photo(media_pk, user_id, directory, username, author)
            except Exception as e:
                print_error(f"download_photo() in handle_queue() failed with: {e}")
        elif media_type_int == 3:
            try:
                download_youtube(media_pk, user_id, directory, username, youtube_id, author)
            except Exception as e:
                print_error(f"download_youtube() in handle_queue() failed with: {e}")

        if status != 403:
            database_functions.update_user_downloads(cursor, user_id, author, media_number)
    except Exception as e:
        print_error(f"handle_queue() - Error processing media: {e}")
    
    database_functions.remove_queue_item(cursor, id)
    time.sleep(random.randint(10,20)/10)


def process_complete_spacer(process):
    print_spacer()
    print_time(f"Finished processing {process}!")
    print_spacer()


def main():
    # Only run handle_threads() if there are any threads
    threads = get_inbox()
    if threads == False:
        print_error(f"Unable to fetch inbox. Ratelimit likely. Check account.")
        input("Press enter when account has been checked")
    elif len(threads) == 0:
        print_error("No new messages found")
        sleep = random.randint(60, 180)
        print_error(f"Sleeping for {round(sleep/60)} minutes. Press Ctrl + C to continue.")
        try:
            time.sleep(sleep)
        except:
            pass
    else:
        handle_threads(threads)
    process_complete_spacer("threads and messages")
    status = status = database_functions.queue_is_empty(cursor)
    # Handle the queue
    while status == False:
        handle_queue()
        status = database_functions.queue_is_empty(cursor)
    process_complete_spacer("queue")

while True:
    main()
    seconds = random.randint(20,50)
    print_time(f"Running cleanup functions.")
    database_functions.update_stats(cursor)
    print_time(f"Main loop completed! Sleeping for {seconds} seconds.")
    time.sleep(seconds)