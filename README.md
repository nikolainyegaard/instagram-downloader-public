# instagram-downloader-public
An automated service to allow users to download any media sent to the host account via Instagram DMs

How it works:

The bot starts by fetching the 20 most recent conversations in the inbox. Then, it reads the last 2 messages from the user in each converation, skipping any mesasges sent from the bots. If any of the 2 messages contains media (posts, stories, links), they get added to the queue.
Please note that after a given conversation has been handled in the inbox, the converastion is deleted from the inbox so the bot doesn't have to process it again later.
Once all 20 of the inbox conversations are processed, it will start looping over the queue and download and send the media to the user from the sender accounts.
Then, it will sleep for 30-50 seconds and start over with the next 20 conversations.

The message depth, i.e. how many messages it reads from each converastion, is determined based on the user's priority level, which can be found in the database. This database will be automatically created the first time you run the script.
The message depth is determined as the priority level +1, so the default level of 1 gives a message depth of 2, and a level of 5 gives a depth of 6.


Instructions on how to use the service:

Install Python.
Run this command to install required packages:
pip install -r requirements.txt

You will need at least two Instagram accounts. One will be the receiver, and the rest will be the senders. The receiver will receive the posts and links from the user, and the senders will send the downloaded media to the users.

In the same directory as your script, you need to create a folder called "Credentials".
Inside "Credentials", create a .txt file for each of the accounts you want to use. The text file should have the same name as the account, i.e. "imagedownloader.1.txt" for the account @imagedownloader.1.
Inside each text file, the first line should be the account username, the second line should be the password, and the third line should be the Instagram account ID for the account. You can find this ID by Goggling "get instagram account id".

Once you have created all your credential text files, open the script "main.py" and edit the lists at the top of the script.
The list "senders_prod" will contain all your senders that the service will be used in production.
The list "senders_test" can be used if you want to do any testing before launching the real accounts.
Enter the information for the admin username and ID, which will be the account which receives messages from the !contact command.
In the list called "admins", enter the username of any accounts you wish to be able to use admin commands from the chat. As of writing this, I'm not actually sure if any of the admin commands are done in the script...

If you want to use the testing accounts, create a text file called "testing.txt" inside the "Credentials" folder, and inside that testing.txt file, write either "true" or "false" for whether you want to use the testing accounts.


Once you have all of this done, you can launch the script from the command line.

The command you need to run is formatted as follows:

python3 main.py <username_of_receiver>

Example:
python3 main.py imagedownloader.1

Afterwards, it will ask for an MFA code. If the account you use does not have MFA set up, just press enter to skip it and continue.


At this point, it should just work!