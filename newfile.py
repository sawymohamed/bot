#pylint:disable=W0611
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import re
import websockets
import asyncio
import json
import string
import urllib
import random
import requests
from urllib.parse import urlencode
from requests_toolbelt.multipart.encoder import MultipartEncoder
import logging
import aiohttp
import time
import threading
from io import BytesIO
from dateutil import tz, zoneinfo
import hashlib
import sqlite3
import yt_dlp as youtube_dl
import ffmpeg
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import sys
import pyshorteners

from collections import defaultdict




from config import BOT_ID, BOT_PWD, GROUP_TO_INIT_JOIN, BOT_MASTER_ID

from plugin_member import mem_user
from plugin_ban import ban_user
from plugin_owner import make_owner
from plugin_admin import make_admin
from plugin_none import none_user
from plugin_kick import kick_user
from plugin_ipban import ipban_user
from plugin_quotes import quotes
from plugin_penalty import penalty_games
from plugin_reminder import hourly_messages


#Database
from database import init_db, add_to_ban_list, remove_from_ban_list, clear_ban_list, is_banned

######### OTHERs ########
ID = "id"
NAME = "name"
USERNAME = "username"
PASSWORD = "password"
ROOM = "room"
TYPE = "type"
HANDLER = "handler"
ALLOWED_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"

########## SOCKET ########
SOCKET_URL = "wss://chatp.net:5333/server"
FILE_UPLOAD_URL = "https://cdn.talkinchat.com/post.php"
######## MSGs #########
MSG_BODY = "body"
MSG_FROM = "from"
MSG_TO = "to"
MSG_TYPE_TXT = "text"
MSG_TYPE_AUDIO = "audio"
MSG_TYPE_INV = "invitation"
MSG_URL = "url"
MSG_LENGTH = "length"
MSG_TYPE_IMG = "image"
########## ------- ##########
######### Handlers #########
HANDLER_LOGIN = "login"
HANDLER_LOGIN_EVENT = "login_event"
HANDLER_ROOM_JOIN = "room_join"
HANDLER_ROOM_LEAVE = "room_leave"
HANDLER_ROOM_EVENT = "room_event"
HANDLER_ROOM_MESSAGE = "room_message"
HANDLER_CHAT_MESSAGE = "chat_message"
HANDLER_PROFILE_UPDATE = "profile_update"
HANDLER_PROFILE_OTHER = "profile_other"
EVENT_TYPE_SUCCESS = "success"
########## ------- ##########
# Global variables Auto Ban
auto_ban_enabled = False

# Global variables Auto Kick
auto_kick_enabled = True

# Variable Max Msg Lenght
MAX_MSG_LENGTH = 1000

# Variable Awaiting Response
awaiting_whom_response = False
target_command = None

# Variable Quit Confirmation
quit_confirmation_pending = False

# Variable untuk set join room
#joined_rooms = set()
joined_rooms = []

# Variable untuk check link detection
check_links = False

# Variable Farewell
msg_leave_enabled = False


# Simpan status permainan dadu
dice_game_status = {}
dice_game_participants = {}

# Variable Ban List
ban_list = set()


#GOOGLE API KEY
GOOGLE_API_KEY = ''


#GOOGLE CSE
GOOGLE_CSE_ID = ''


#GOOGLE CX
#GOOGLE_SEARCH_CX = ""


# Konfigurasi OpenAI
#openai.api_key = ''

clckru = ""

# Struktur data untuk menyimpan waktu pengguna bergabung per grup
user_join_times = defaultdict(dict)  # {room: {user_id: last_join_time}}



AUDIO_DURATION = 0
LAST_MUSIC_URL = ''


s = pyshorteners.Shortener()



ydl_opts = {
    'quiet': True,
    'noplaylist': True
}




# Load self newbot.py
async def load_self():
    try:
        # Pastikan file ini bisa di-load ulang
        script_path = sys.argv[0]
        
        if os.path.exists(script_path):
            with open(script_path, "r") as file:
                code = file.read()
                exec(code, globals())
            return "✅ newbot.py reloaded successfully"
        else:
            return "newbot.py not found."
    except Exception as e:
        return f"An error occurred while reloading newbot.py : {str(e)}"


# Load Plugin
async def load_plugin(plugin_name):
    try:
        plugin_path = f"{plugin_name}.py"
        
        if os.path.exists(plugin_path):
            with open(plugin_path, "r") as file:
                code = file.read()
                exec(code, globals())
            return f"✅ plugin {plugin_name} loaded successfully"
        else:
            return f"❗ plugin {plugin_name} not found"
    except Exception as e:
        return f"An error occurred while loading plugin {plugin_name} : {str(e)}"

# Remove Html Status
def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
    
    
# Dice Random
def generate_random_number():
    return random.randint(1, 100)

# Status permainan dadu dan peserta
dice_game_status = {}
dice_game_participants = {}

async def start_dice_game(ws, room):
    global dice_game_status, dice_game_participants
    
    # Mulai permainan dadu
    dice_game_status[room] = 'started'
    dice_game_participants[room] = {}
    
    await send_group_msg(ws, room, "The dice game has started ! 🎲 Send the command `.roll` to roll the dice.")

async def roll_dice(ws, room, user):
    if dice_game_status.get(room) != 'started':
        await send_group_msg(ws, room, "The dice game hasn’t started yet.\nSend `game` to see the commands 🎲")
        return
    
    roll_result = generate_random_number()
    
    if user not in dice_game_participants[room]:
        dice_game_participants[room][user] = roll_result
        await send_private_msg(ws, user, f"🎲 You've rolled the dice and got a number ({roll_result})")
        await send_group_msg(ws, room, f"🎲 {user} has rolled the dice and gotten a number (**)")
    else:
        await send_group_msg(ws, room, "You've rolled the dice wait for the result")

async def end_dice_game(ws, room):
    if dice_game_status.get(room) != 'started':
        await send_group_msg(ws, room, "The dice game hasn’t started yet.\nSend `game` to see the commands 🎲")
        return

    # Tentukan nilai dadu terendah
    if not dice_game_participants.get(room):
        await send_group_msg(ws, room, "There are no participants in the dice game")
        return
    
    lowest_roll = min(dice_game_participants[room].values())
    losers = [user for user, roll in dice_game_participants[room].items() if roll == lowest_roll]
    
    await send_group_msg(ws, room, f"⏳ Please wait 15 seconds to calculate the result")
    await asyncio.sleep(15)
    
    scores_message = "\n".join([f"ID : {user} 🎲 Score : ({roll})" for user, roll in dice_game_participants[room].items()])
    await send_group_msg(ws, room, f"🏆 Final result :\n{scores_message}")
    
    for loser in losers:
        await kick_user(ws, room, loser, "Lost the dice game.")
    
    await send_group_msg(ws, room, f"🎲 Dice game is over ! The user with the lowest roll ({lowest_roll}) has been kicked : {', '.join(losers)}")
    
    # Reset status permainan
    dice_game_status[room] = 'ended'
    dice_game_participants[room] = {}
    

# clckru
async def on_user_joined(ws, data):
    """Handler ketika pengguna bergabung ke grup."""
    room = data[ROOM]
    user_id = data[MSG_FROM]
    join_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Format waktu

    # Simpan waktu bergabung pengguna di grup
    user_join_times[room][user_id] = join_time

#bot replay
async def send_group_msg(ws, room, message):
        if "bot" in msg:
         await send_group_msg(ws, room, "عيوني 🥰")
         
    # Logika lain jika ada...

async def show_recent_joins(ws, room):
    """Menampilkan 10 pengguna terakhir yang bergabung ke grup."""
    if room not in user_join_times or not user_join_times[room]:
        await send_group_msg(ws, room, "No users have joined recently.")
        return

    # Ambil pengguna yang bergabung diurutkan berdasarkan waktu (paling baru ke lama)
    sorted_users = sorted(user_join_times[room].items(), key=lambda x: x[1], reverse=True)

    # Ambil hingga 10 pengguna terakhir
    recent_joins = sorted_users[:10]

    # Format pesan yang akan dikirim
    response = "Recent 10 user joins :\n"
    for idx, (user_id, join_time) in enumerate(recent_joins, start=1):
        response += f"{idx}. User : {user_id}, Last Joined : {join_time}\n"

    await send_group_msg(ws, room, response)


# Bitly, clckru, Tc
def shorten_url(url, bitly_access_token):
    s = pyshorteners.Shortener()

    bitly_short_url = None
    clckru_short_url = None
    should_use_bitly = False

    try:
        s = pyshorteners.Shortener(api_key=bitly_access_token)
        bitly_short_url = s.bitly.short(url)
        should_use_bitly = True
    except Exception as e:
        print(f"Error shortening URL with Bitly : {e}")

    try:
        clckru_short_url = s.clckru.short(url)
    except Exception as e:
        print(f"Error shortening URL with clckru : {e}")

    if should_use_bitly and bitly_short_url:
        final_url = bitly_short_url
    elif clckru_short_url:
        final_url = clckru_short_url
    else:
        final_url = url

    return final_url


# Contoh penggunaan
bitly_access_token = ''



# Scrape Music From Youtube
def scrape_music_from_youtube(search_query):
    ydl_opts = {
        'format': 'bestaudio/best',  # Ambil format audio terbaik
        'noplaylist': True,          # Hanya ambil video tunggal
        'quiet': False,              # Matikan log output
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"ytsearch:{search_query}", download=False)
            if 'entries' in result and len(result['entries']) > 0:
                video_info = result['entries'][0]
                title = video_info.get('title', 'Unknown Title')
                formats = video_info.get('formats', [])
                # Temukan format audio terbaik
                for data in formats:
                    if data.get('acodec') in ['mp4a.40.2', 'opus', 'mp3']:  # Format codec audio yang umum
                        return {
                            'url': data.get('url', ''),
                            'title': title
                        }
        except Exception as e:
            print(f"An error occurred while fetching music : {e}")

    return None

    


# Zona waktu Indonesia
INDONESIA_TZ = pytz.timezone('Asia/Jakarta')

async def send_group_msg(ws, room, message):
    """Fungsi untuk mengirim pesan ke grup."""
    try:
        await ws.send(json.dumps({
            "room": room,
            "message": message
        }))
    except Exception as e:
        print(f"Error sending message : {str(e)}")

async def send_hourly_reminder(ws):
    while True:
        now = datetime.now(INDONESIA_TZ)
        current_hour = now.strftime("%H")
        
        # Pilih pesan berdasarkan jam
        reminder_message = hourly_messages.get(current_hour, "Waktu berjalan cepat 😊")
        
        for room in joined_rooms:
            try:
                # Kirim pesan pengingat
                await send_group_msg(ws, room, reminder_message)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed while sending reminder. Reconnecting...")
                break  # Breaks out of the while loop to reconnect
            except Exception as e:
                print(f"Error in send_hourly_reminder : {str(e)}")
        
        # Tunggu hingga jam berikutnya
        next_hour = now + timedelta(hours=1)
        next_hour = next_hour.replace(minute=0, second=0, microsecond=0)
        wait_time = (next_hour - now).total_seconds()
        await asyncio.sleep(wait_time)



# Menangani perintah -bl ID untuk menghapus ID dari blacklist
async def handle_remove_from_ban_list(ws, room, frm, target_id):
    if is_banned(target_id):
        remove_from_ban_list(target_id)
        await send_private_msg(ws, frm, f"✅ {target_id} removed from blacklist")
        await send_group_msg(ws, room, f"✅ {target_id} removed from blacklist")
    else:
        await send_private_msg(ws, frm, f"❗ {target_id} is not in the blacklist")
        await send_group_msg(ws, room, f"❗ {target_id} is not in the blacklist")



# Menangani perintah .show bl untuk menampilkan daftar blacklist
async def handle_show_ban_list(ws, room, frm):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT id FROM ban_list')
    ban_list = c.fetchall()
    conn.close()

    if ban_list:
        ban_list_str = '\n'.join([f"{i+1}. {row[0]}" for i, row in enumerate(ban_list)])
        await send_group_msg(ws, room,
        f"🗒️ black List :\n"
        f"{ban_list_str}")
    else:
        await send_group_msg(ws, room, "🚫 the blacklist is empty")



tempRoom=""
dstatus = "<p style='background-color:black'><font color='green'>master : <b>ڤخــ°○ــٱمھ∫♜∫شــ○°ــمريــے</b><br><br> </b>main room : عشق<b></b><br><br></b>ABOT V 1.1.0<br><br>send <b>FUN</b> to see a list of <b>FUN</b> commands</font></p>"


# Mengatur logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    
#Love Calculate
async def calculate_love(ws, room, user1, user2):
    combined_names = (user1 + user2).encode('utf-8')
    hash_value = hashlib.sha256(combined_names).hexdigest()
    love_score = int(hash_value[:2], 16) % 101

    # Menentukan komentar berdasarkan skor cinta
    if love_score >= 90:
        comment = "are a perfect match! 💕"
    elif love_score >= 70:
        comment = "have great chemistry! 💖"
    elif love_score >= 50:
        comment = "get along well enough. 💞"
    elif love_score >= 30:
        comment = "may need to work on their relationship. 💔"
    elif love_score >= 10:
        comment = "have a rocky road ahead. 🥀"
    else:
        comment = "are not really compatible. 💀"

    love_message = f"The love percentage between {user1} and {user2} is : {love_score}%\n{user1} and {user2} {comment}"
    await send_group_msg(ws, room, love_message)

                
#Black List        
async def handle_ban_list(ws, room, frm, target_id):
    if not is_banned(target_id):
        add_to_ban_list(target_id)
        await send_private_msg(ws, frm, f"🚫 {target_id} has been blacklisted")
        await send_group_msg(ws, room, f"🚫 {target_id} has been blacklisted")
    else:
        await send_private_msg(ws, frm, f"⚠️ {target_id} is already in the blacklist 🚫")
        await send_group_msg(ws, room, f"⚠️ {target_id} is already in the blacklist 🚫")

async def handle_reset_ban_list(ws, room, frm):
    if frm in BOT_MASTER_ID:
        clear_ban_list()
        await send_private_msg(ws, frm, "🔄 blacklist has been reset")
        await send_group_msg(ws, room, f"🔄 {frm} has reset the blacklist")
    else:
        await send_private_msg(ws, frm, "🚫 You do not have permission to reset the blacklist")




async def fetch_image_url(query):
    search_url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&cx={GOOGLE_CSE_ID}&searchType=image&key={GOOGLE_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                data = await response.json()
                if data.get('items'):
                    # Mengambil URL gambar pertama
                    image_url = data['items'][0]['link']
                    return image_url
                else:
                    return None
    except Exception as e:
        print(f"Error fetching image from Google : {e}")
        return None


# Auto Posting
async def auto_post_message(ws, room, message):
    while True:
        await send_group_msg(ws, room, message)
        await asyncio.sleep(1200)



async def send_pvt_msg_d(ws, room, frm, target_id):
    jsonbody = {HANDLER: HANDLER_CHAT_MESSAGE, ID: gen_random_str(20), MSG_TO: target_id, TYPE: MSG_TYPE_TXT, MSG_BODY: f"You have received an invitation from\n"
    f"🆔 : {frm}\n"
    f"🏠 : {room}"}
    await ws.send(json.dumps(jsonbody, ensure_ascii=False))
    
    await send_group_msg(ws, room, f"✅ invite sent to {target_id}")


# Send Kiss
async def send_private_kiss_message(ws, room, frm, user, message):
    kiss_message = f"{frm} sends you a kiss 😘\nMessage : {message}"  # Customize your kiss message here
    jsonbody = {
        HANDLER: HANDLER_CHAT_MESSAGE,
        ID: gen_random_str(20),
        MSG_TO: user,
        TYPE: MSG_TYPE_TXT,
        MSG_URL: "",
        MSG_BODY: kiss_message,
        MSG_LENGTH: ""
    }
    await ws.send(json.dumps(jsonbody))
    await send_group_msg(ws, room, f"💋 a kiss has been sent to {user} by {frm}")



# Auto-add friend requests. lol
async def cid_add(ws, data):
    send_add = data['users']
    if len(send_add) < 1:
        await asyncio.sleep(1)        
    else:
        send_add = data['users'][0]['username']
        ddd = {"handler": "profile_update", "id": gen_random_str(20), "type": "accept_friend", "value": send_add}
        await ws.send(json.dumps(ddd))
        await send_private_msg(ws, send_add, f"{send_add} 😍\nSend HELP to get started")



async def fetchUserProfile(ws,targetId, room):
    jsonbody = { HANDLER: HANDLER_PROFILE_OTHER, ID: gen_random_str(20), TYPE: targetId }
    global tempRoom
    tempRoom = room[:]
    await ws.send(json.dumps(jsonbody))


# Set Status Bot
async def set_status(ws, status):
    statusPayload = {
        "handler": HANDLER_PROFILE_UPDATE,
        "id": gen_random_str(20),
        "type": "status",
        "value": dstatus
    }
    await ws.send(json.dumps(statusPayload))


async def send_group_msg_image(ws, room, url):
    jsonbody = {HANDLER: HANDLER_ROOM_MESSAGE, ID: gen_random_str(20), ROOM: room, TYPE: MSG_TYPE_IMG, MSG_URL: url, MSG_BODY: "", MSG_LENGTH: ""}
    await ws.send(json.dumps(jsonbody, ensure_ascii = False))



async def set_max_msg_length(ws, room, length):
    global MAX_MSG_LENGTH
    try:
        MAX_MSG_LENGTH = int(length)
        await send_group_msg(ws, room, f"📝 Max Message Length : ({MAX_MSG_LENGTH}) Char.")
    except ValueError:
        await send_group_msg(ws, room, "❌ invalid length value")



async def send_private_msg(ws, user, msg):
    jsonbody = {
        HANDLER: HANDLER_CHAT_MESSAGE,
        ID: gen_random_str(20),
        MSG_TO: user,
        TYPE: MSG_TYPE_TXT,
        MSG_URL: "",
        MSG_BODY: msg,
        MSG_LENGTH: ""
    }
    await ws.send(json.dumps(jsonbody))
    
    
async def send_pvt_msg(ws, user, msg):
    jsonbody = {
        HANDLER: HANDLER_CHAT_MESSAGE,
        ID: gen_random_str(20),
        MSG_TO: user,
        TYPE: MSG_TYPE_TXT,
        MSG_URL: "",
        MSG_BODY: msg,
        MSG_LENGTH: ""
    }
    await ws.send(json.dumps(jsonbody))

    
#Private message Bot   
async def on_private_message(ws, data):
    try:
        msg = data.get(MSG_BODY, "").lower()
        #original msg
        msg = data.get(MSG_BODY, "")
        frm = data.get(MSG_FROM, "")
        
        
        
        # Join Another Group
        if frm in BOT_MASTER_ID and msg.startswith(".join "):
        	new_room = msg[6:].strip()
        	if new_room:
        	   	if new_room in joined_rooms:
        	   		await send_pvt_msg(ws, frm, f"I'm already in {new_room} 😐")
        	   	else:
        	   		await join_group(ws, new_room)
        	   		await send_pvt_msg(ws, frm, f"Joining room {new_room} 🚀")
        	   		
        	   		
        # Leave Current Group .quit number
        if msg.startswith(".quit ") and frm in BOT_MASTER_ID:
        	target_room = msg[6:].strip()
        	if target_room.isdigit():
        	   index = int(target_room) - 1
        	   if 0 <= index < len(joined_rooms):
        	       room_to_quit = list(joined_rooms)[index]
        	       await leave_group(ws, room_to_quit)
        	       await send_pvt_msg(ws, frm, f"Leaving room {room_to_quit} 🚪")
        	   else:
        	   	await send_pvt_msg(ws, frm, "⚠️ Please specify a valid room number\n\nEx : .quit 1")
        	   	
        	   	
        	   	
    # List Joined Rooms with Ascending Numbers
        if msg.startswith(".ls") and frm in BOT_MASTER_ID:
        	if joined_rooms:
        		rooms_list = "\n".join(f"{i}. {room}" for i, room in enumerate(joined_rooms, start=1))
        	await send_pvt_msg(ws, frm, f"Bot is in the following rooms : \n{rooms_list}")
        	
        	
        if msg.strip().lower() == ("command"):
            	await send_private_msg(ws, frm, "send h1 to see the command")
        	
        	
        	
        # Help commands for all users
        if msg.strip().lower() == ("help"):
            await send_private_msg(ws, frm, "🔧 Send [command] to see the list of available commands !\n\nℹ️ Send [info] to get information about this bot !\n\n🎉 Send [fun] to see a list of fun commands !")
            
            

        if msg.strip().lower() == ("info"):
            await send_private_msg(ws, frm, "ABOT V 1.1.0\nCreated By Saheer🚫\nTalkinChat : ڤخــ°○ــٱمھ∫♜∫شــ○°ــمريــے ✅")
            
            
        if msg.strip().lower() == ("fun"):
            await send_private_msg(ws, frm, "🔎 .pro ID view user profile\n🎲 .rol rollers for dice games\n🕒 .time check the time\n😘 .kiss ID to send a kiss to another person\n🚀 .i ID invite users to join the room\n🖼️ .img text or message to perform an image search\n💓 .love ID1 ID2 to check the level of love\n👟 kick me (to kick yourself)\ngame To see available games")
 
            	
            
        if msg.strip().lower() == ("h1"):
            await send_private_msg(ws, frm, ".k ID kick user 👟\n.n ID remove permission 🚫\n.m ID make a member 👤\n.a ID make admin 🛡️\n.o ID make the owner 👑\n\nsend h2 for next command")
            
            
        if msg.strip().lower() == ("h2"):
            await send_private_msg(ws, frm, ".ml num set max message length 📏\n.mas ID add user as bot master 👑\n.link on activate link detection 🔗\n.link off inactive link detection 🚫🔗\n.fr on activate farewell 👋\n\nsend h3 for the next command 💬")
            
            
        if msg.strip().lower() == ("h3"):
            await send_private_msg(ws, frm, ".fr off inactive farewell 🚫👋\n.ak on activate auto kick 🚀\n.ak off inactive auto kick 🚫🚀\n.ab on activate auto ban 🔨\n.ab off inactive auto ban 🚫🔨\n\nsend h4 for next command 💬")
            
            
        if msg.strip().lower() == ("h4"):
        	await send_private_msg(ws, frm, "+bl ID add ID to black list 🚫\n-bl ID remove ID from blacklist ❌🚫\n.res bl reset black list 🔄🚫\n.show bl view black list 👁️🚫\n.join <room_name> 🏠\n\ncommand list complete. ✔️")


    except Exception as e:
        print(f"Error in on_private_message : {e}")
        
        
        
# on_message
async def on_message(ws, data):
    global awaiting_whom_response, target_command
    global check_links
    global spin_enabled
    global msg_leave_enabled
    global attendance_check_active, attended_users
    global auto_kick_enabled
    global auto_ban_enabled
    #logging.info(f"Message received: {data}")
    try:
        msg = data.get(MSG_BODY, "").lower()
        #msg original
        msg = data.get(MSG_BODY, "")
        frm = data.get(MSG_FROM, "")
        room = data.get(ROOM, "")
        username = data.get(USERNAME, "")
        user_id = data.get('user_id', '')
        user_avatar_url = data.get('photo_url')

        if frm == BOT_ID:
            return
            
        # Perintah untuk menampilkan waktu join 10 pengguna terakhir
        if msg == ".rec":
        	await show_recent_joins(ws, room)
        	return
            
            
        # +play <song name>
        if msg.startswith("شغل "):
        	global LAST_MUSIC_URL
        	search_music = msg[4:]
        	
        	try:
        		music_info = scrape_music_from_youtube(search_music)
        		
        		if music_info and music_info['url']:
        		  bitly_access_token = 'a048d0816ad1217887c92e767753f236a7755f2e'
        		  short_url = shorten_url(music_info['url'], bitly_access_token)
        		  
        		  formatted_message = (
        		  f"🎉 Download Complete!\n"
        		  f"🎵 Title: {music_info['title']}\n"
        		  f"🔍 Search Query: {search_music}\n"
        		  f"🔄 Request Processed Successfully!")
        		  
        		  await send_group_msg(ws, room, formatted_message)
        		  await send_group_msg_audio(ws, room, frm, short_url)
        		else:
        			await send_group_msg(ws, room, f"❌ No song found for 🎵 {search_music} !")
        			
        	except Exception as e:
        		await send_group_msg(ws, room, f"An error occurred : {e}")
        
        
            
        if frm in BOT_MASTER_ID:
        	if msg.startswith("load "):
        		plugin_name = msg.split(" ", 1)[1].strip()
        		# Load self
        		if plugin_name == "self":
        			
        			response = await load_self()
        		else:
        			response = await load_plugin(plugin_name)
        			await send_group_msg(ws, room, response)
        			return
            
            
        # .startdice untuk memulai game
        if msg.startswith('.startdice'):
        	await start_dice_game(ws, room)
        	
        # .roll untuk melempar dadu
        elif msg.startswith('.roll'):
        	await roll_dice(ws, room, frm)
        		
        # .enddice untuk mengakhiri	
        elif msg.startswith('.enddice'):
        	await end_dice_game(ws, room)
            
        # .love ID1 ID2 kalkulasi cinta
        if msg.startswith(".love"):
               args = msg.split()
        # Pastikan ada cukup argumen
               if len(args) == 3:
                    user1 = args[1]
                    user2 = args[2]
                    await calculate_love(ws, room, user1, user2)
               else:
                    await send_group_msg(ws, room, "usage : .love ID1 ID2")
         
         
        #  .q untuk random quotes
        if msg.strip().lower() == ("q"):
            random_quote = random.choice(quotes)
            await send_group_msg(ws, room, random_quote)
            
            
        	
        	
        # +bl ID untuk menambahkan daftar ID ke dalam blacklist database	
        if frm in BOT_MASTER_ID:
        	if msg.startswith("+bl "):
        		target_id = msg.split()[1]
        		await handle_ban_list(ws, room, frm, target_id)
        		
        		
        # .res bl reset blacklist menghapus semua daftar blacklist dari database
        if frm in BOT_MASTER_ID:
        	 if msg.startswith(".res bl"):
        	   await handle_reset_ban_list(ws, room, frm)

            
        # -bl ID untuk menghapus dari daftar blacklist
        if frm in BOT_MASTER_ID:
        	if msg.startswith('-bl '):
        		target_id = msg[4:].strip()
        		await handle_remove_from_ban_list(ws, room, frm, target_id)
        	
        	
        # .show bl untuk menampilkan daftar blacklist
        if msg.strip().lower() == ".show bl" and frm in BOT_MASTER_ID:
            await handle_show_ban_list(ws, room, frm)
            
       
       
       # +mas ID add new master bot
        if msg.startswith("+mas ") and frm in BOT_MASTER_ID:
               new_master_id = msg[len(".mas "):].strip()
               if new_master_id and new_master_id not in BOT_MASTER_ID:
                     BOT_MASTER_ID.append(new_master_id)
                     
                     await send_group_msg(ws, room, f"{frm} has added master\n🆔 : {new_master_id}")
               else:
                     await send_group_msg(ws, room, "⚠️ This user is already a bot master ! 🤖")
            
            
               
    # Menangani perintah .ab on dan .ab off hanya untuk BOT_MASTER_ID
        if frm in BOT_MASTER_ID:
            if msg.strip().lower() == (".ab on"):
            	auto_ban_enabled = True
            	await send_group_msg(ws, room, "🚨 Auto Ban Activated ! 🚫🔒")
            	return

            if msg.strip().lower() == (".ab off"):
            	auto_ban_enabled = False
            	await send_group_msg(ws, room, "⚠️ Auto Ban Deactivated ! 🚫🔓")
            	return
      

    # Menangani perintah .ak on dan .ak off hanya untuk BOT_MASTER_ID
        if frm in BOT_MASTER_ID:
            if msg.strip().lower() == (".ak on"):
            	auto_kick_enabled = True
            	await send_group_msg(ws, room, "🚨 Auto Kick Activated ! 🚪🔧")
            	return

            if msg.strip().lower() == (".ak off"):
                auto_kick_enabled = False
                await send_group_msg(ws, room, "⚠️ Auto Kick Deactivated ! 🚫🔧")
                return
                

#===============================#
# fun commands

        if msg.strip().lower() == ("fun"):
            await send_group_msg(ws, room, f"🔎 .pro ID view user profile\n🎲 .rol rollers for dice games\n🕒 .time check the time\n😘 .kiss ID to send a kiss to another person\n🚀 .i ID invite users to join the room\n🖼️ .img text or message to perform an image search\n💓 .love ID1 ID2 to check the level of love\n👟 kick me (to kick yourself)\n🎲 game To see available games")
            
            
#Dice Game
        if msg.strip().lower() == ("game"):
            await send_group_msg(ws, room, f".startdice 🎲 to start the game\n.roll 🎲 to roll the dice\n.enddice 🎉 to end the game\n\n• Type .enddice when no users are rolling the dice\n\n• All users can participate in this game")
            
           

        if frm in BOT_MASTER_ID:
             if msg.strip().lower() == (".fr on"):
                    msg_leave_enabled = True
                    await send_group_msg(ws, room, "📩 Farewell Messages Activated ! 👋")
                    return
             elif msg.strip().lower() == (".fr off"):
                    msg_leave_enabled = False
                    await send_group_msg(ws, room, "⚠️ Farewell Messages Deactivated ! 🚫📩")
                    return

#===============================#
# .link on

        # Mengendalikan fitur link on/off
        if msg.strip().lower() == ".link on" and frm in BOT_MASTER_ID:  # Pastikan hanya master bot yang bisa mengaktifkan
               check_links = True
               await send_group_msg(ws, room, "🔗 Link Detection Activated ! 👁️")
               return
        elif msg.strip().lower() == ".link off" and frm in BOT_MASTER_ID:  # Pastikan hanya master bot yang bisa menonaktifkan
               check_links = False
               await send_group_msg(ws, room, "⚠️ Link Detection Deactivated ! 🚫🔗")
               return

    # Jika fitur pengecekan link aktif, cek pesan
        if check_links:
             url_pattern = r'(https?://[^\s]+)'
             if re.search(url_pattern, msg):
                 warning_message = f"🚫 {frm}, sending links is not allowed. You are being removed from the room."
                 await send_group_msg(ws, room, warning_message)
                 await kick_user(ws, room, frm)
                 return
            
#===============================#

# .i ID
        if msg.startswith(".i "):
            target_id = msg[3:]          
            await send_pvt_msg_d(ws, room, frm, target_id)
            
#===============================#

#.img text or message
        if msg.startswith("صورة "):
               query = msg[4:].strip()
               if query:
                     image_url = await fetch_image_url(query)
                     if image_url:
            # Mengirim pesan dengan tipe image
                          await send_group_msg(ws, room, image_url, msg_type=MSG_TYPE_IMG)
                     else:
                          await send_group_msg(ws, room, "Can't find image")
                          
#===============================#

# kick me
        if msg.strip().lower() == ("اطردني"):
               await send_group_msg(ws, room, f"🚪 {frm} تم طردك بنجاح مع السلامة 🥺")
               await kick_user(ws, room, frm)  # Gunakan username atau ID sesuai yang diperlukan
               return
    
#===============================#

        # Handle .kiss command with a message
        if msg.startswith(".kiss "):
            parts = msg.split(maxsplit=2)
            if len(parts) < 2:
                # Jika perintah .kiss tidak diikuti oleh ID pengguna, kirimkan pesan "whom?"
                await send_private_msg(ws, frm, "Whom ?")
            else:
                kiss_user = parts[1].strip()
                kiss_message = parts[2].strip() if len(parts) > 2 else ""  # Ambil pesan tambahan jika ada
                if kiss_user:
                    await send_private_kiss_message(ws, room, frm, kiss_user, kiss_message)
                else:
                    await send_private_msg(ws, frm, "Invalid command. Please use .kiss <user_id> [message]")
            
#===============================#

# .cancel all commands

        if msg.strip().lower() == ("@"):
               if awaiting_whom_response and frm in BOT_MASTER_ID:
                     await send_group_msg(ws, room, "❌ command cancelled")
                     awaiting_whom_response = False
                     target_command = None
                     return

# .m ID make a member
        if frm in BOT_MASTER_ID and msg == ".m":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "mem_user"
            
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "mem_user":
                await mem_user(ws, room, msg)
                awaiting_whom_response = False
                target_command = None
                return
                
                
        if msg.startswith(".m ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await mem_user(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
                
#===============================#

# .ml Num set max message length
        if msg.startswith(".ml ") and frm in BOT_MASTER_ID:
               parts = msg.split()
               if len(parts) == 2:
                   new_length = parts[1]
                   await set_max_msg_length(ws, room, new_length)
               else:
                   await send_group_msg(ws, room, "📋 usage: `.ml num`")
               return
               
        if len(msg) > MAX_MSG_LENGTH:
             if frm != BOT_ID and frm not in BOT_MASTER_ID:
                   await kick_user(ws, room, frm)
                   await send_group_msg(ws, room, f"🚪 {frm} was kicked\nreason : {MAX_MSG_LENGTH} Char")
                   return
         
#===============================#
         
# .n ID remove permission
        if frm in BOT_MASTER_ID and msg == ".n":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "none_user"
            
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "none_user":
                await none_user(ws, room, msg)
                awaiting_whom_response = False
                target_command = None

                return
                
                
        if msg.startswith(".n ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await none_user(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
              
#===============================#

# .b ID banned a user
        if frm in BOT_MASTER_ID and msg == ".b":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "ban_user"
            
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "ban_user":
                await ban_user(ws, room, msg)
                awaiting_whom_response = False
                target_command = None
                
                return
                
                
        if msg.startswith(".b ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await ban_user(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
                    
#===============================#
# .bip ID ban IP

        if frm in BOT_MASTER_ID and msg == ".ip":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "ipban_user"
            
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "ipban_user":
                await ipban_user(ws, room, msg)
                awaiting_whom_response = False
                target_command = None
                
                return

            
        if msg.startswith(".bip ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await ipban_user(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
                
#===============================#

# .k ID kick a user
        if frm in BOT_MASTER_ID and msg == ".k":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "kick_user"
            
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "kick_user":
                await kick_user(ws, room, msg)
                awaiting_whom_response = False
                target_command = None
                
                return
                
                
        if msg.startswith(".k ") and frm in BOT_MASTER_ID:
               target_username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if target_username:
                    await kick_user(ws, room, target_username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")

#===============================#

# .o ID make owner
        if frm in BOT_MASTER_ID and msg == ".o":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "make_owner"  # Misalnya, command yang ingin dilakukan setelah mendapat respons
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "make_owner":
                await make_owner(ws, room, msg)
                awaiting_whom_response = False  # Reset status menunggu
                target_command = None  # Reset command target
                return
                
                
        if msg.startswith(".o ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await make_owner(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
                
#===============================#

# .a ID make admin

        if frm in BOT_MASTER_ID and msg == ".a":
            await send_group_msg(ws, room, "🔍 Whom ?")
            awaiting_whom_response = True
            target_command = "make_admin"  # Misalnya, command yang ingin dilakukan setelah mendapat respons
            return

        if awaiting_whom_response and frm in BOT_MASTER_ID:
            if target_command == "make_admin":
                await make_admin(ws, room, msg)
                awaiting_whom_response = False  # Reset status menunggu
                target_command = None  # Reset command target
                return
                
                
        if msg.startswith(".a ") and frm in BOT_MASTER_ID:
               username = msg.split(" ")[1] if len(msg.split(" ")) > 1 else ""
               if username:
                    await make_admin(ws, room, username)
               else:
                    await send_group_msg(ws, room, "Please specify a username.")
                    
#===============================#
                           
# Auto respon             
        """if "jaka" in msg:
                 await send_pvt_msg(ws, frm, "Don't tag 'Jaka' or you will get kicked")"""
                 
        
        
        
# Add more games for fun
        if msg.lower() == (".rol") or msg.lower() == (".Rol"):
           rol_d = random.randint(0,100)
           await send_group_msg(ws, room, f" {frm}\n 🎲 🎲\n Number :『 {rol_d} 』")



# time for checking time at indo
        if msg.lower() == (".time"):
            d = tz.gettz("indo")
            now = datetime.now(tz=d)
            await send_group_msg(ws, room, f"╭─━━━━━━━━━━━─╮\n│ 🕰 Clock and Date\n│ 📅 Today : {now.strftime('%A')}\n│ 📆 Date : {now.strftime('%d')} \n│ 📅 Month : {now.strftime('%B')}\n│ 📆 Year : {now.strftime('%Y')}\n│ ⏰ Time : {now.strftime('%I:%M %p')} 🕒  \n╰─━━━━━━━━━━━─╯")





# +pro ID view user profile
        if msg.startswith(".pro "):
            target_id = msg[5:]
            tempRoom = room[:]
            await fetchUserProfile(ws,target_id, room)



        # Join Another Group
        if frm in BOT_MASTER_ID and msg.startswith(".join "):
        	new_room = msg[6:].strip()
        	if new_room:
        	   	if new_room in joined_rooms:
        	   		await send_group_msg(ws, room, f"I'm already in {new_room} 😐")
        	   	else:
        	   		await join_group(ws, new_room)
        	   		await send_group_msg(ws, room, f"Joining room {new_room} 🚀")
        	   		
    except Exception as e:
       print(f"An error occurred : {e}")
       
            
    
    
        # Leave Current Group .quit number
    if msg.startswith(".quit ") and frm in BOT_MASTER_ID:
        	target_room = msg[6:].strip()
        	if target_room.isdigit():
        	   index = int(target_room) - 1
        	   if 0 <= index < len(joined_rooms):
        	       room_to_quit = list(joined_rooms)[index]
        	       await leave_group(ws, room_to_quit)
        	       await send_group_msg(ws, room, f"Leaving room {room_to_quit} 🚪")
        	   else:
        	   	await send_group_msg(ws, room, "⚠️ Please specify a valid room number")
        	   	
        	   	
        	   	
    # List Joined Rooms with Ascending Numbers
    if msg.startswith(".ls") and frm in BOT_MASTER_ID:
        if joined_rooms:
        	rooms_list = "\n".join(f"{i}. {room}" for i, room in enumerate(joined_rooms, start=1))
        	await send_group_msg(ws, room, f"Bot is in the following rooms : \n{rooms_list}")
        else:
        		await send_group_msg(ws, room, "🚫 the bot is not in any rooms")
        		
        		
# Send Group Message Audio
async def send_group_msg_audio(ws, room, frm, url):
    try:
        bitly_access_token = 'a048d0816ad1217887c92e767753f236a7755f2'
        final_url = shorten_url(url, bitly_access_token)

        audio_msg = {
            'handler': 'room_message',
            'id': gen_random_str(20),
            'room': room,
            'type': 'audio',
            'url': final_url,
            'body': '',
            'length': '0'
        }

        print(f"Final URL : {final_url}")
        await ws.send(json.dumps(audio_msg))
        print("Audio message sent successfully")
        
    except Exception as e:
        print(f"An error occurred while sending audio message : {e}")
        
        
       
async def login(ws):
    jsonbody = {HANDLER: HANDLER_LOGIN, ID: gen_random_str(20), USERNAME: BOT_ID, PASSWORD: BOT_PWD}
    #print(jsonbody)
    await ws.send(json.dumps(jsonbody))
    

# Joined Group
async def join_group(ws, group):
    jsonbody = {
        HANDLER: HANDLER_ROOM_JOIN,
        ID: gen_random_str(20),
        NAME: group
    }
    await ws.send(json.dumps(jsonbody))
    joined_rooms.append(group)
    
    
# Leave Joined Group
async def leave_group(ws, room):
    jsonbody = {
        HANDLER: HANDLER_ROOM_LEAVE,
        NAME: room,
        ID: gen_random_str(20)
    }
    await ws.send(json.dumps(jsonbody))
    
    # Hapus room dari joined_rooms jika ada
    if room in joined_rooms:
        joined_rooms.remove(room)

    
#Send Image
async def send_group_msg(ws, room, msg, msg_type=MSG_TYPE_TXT):
    jsonbody = {
        HANDLER: HANDLER_ROOM_MESSAGE,
        ID: gen_random_str(20),
        ROOM: room,
        TYPE: msg_type,
        MSG_URL: "" if msg_type == MSG_TYPE_TXT else msg,
        MSG_BODY: msg if msg_type == MSG_TYPE_TXT else "",
        MSG_LENGTH: "",
    }
    await ws.send(json.dumps(jsonbody, ensure_ascii=False))
    
        

# Welcome User
async def wc_user_msg(ws, data):
    room = data['name']
    frm = data['username']
    role = data["role"]
    
    # Periksa apakah pengguna ada di ban_list
    #if frm in ban_list:
        #await ban_user(ws, room, frm, "ID is in the ban list")
        #return
        
    # ID blacklisted    
    if is_banned(frm):
        await ban_user(ws, room, frm, "ID blacklisted")
        return

    role_str = {
        'member': "الرتبة عضو جديد",
        'admin': "الرتبة مشرف",
        'owner': "الرتبة مالك الغرفة",
        'none': "الرتبة زائر",
        'creator': "الرتبة صانع الغرفة 🌟"
    }.get(role, "unknown role (none)")

    special_welcome_messages = {
        '' : "Failed to greet",
        '' : "mrs.ceres 🍼",
        '' : "frog king 🐸",
        '' : "welcome kk lee sayang😘"
    }

    bot_master_welcome = "🦁 دخول مميز لماستر البوت 🦁"

    if role == 'none':
        if auto_kick_enabled:
            await kick_user(ws, room, frm, "not a member")
            return
        elif auto_ban_enabled:
            await ban_user(ws, room, frm, "not a member")
            return

    if frm in BOT_MASTER_ID:
        welcome_message = bot_master_welcome
    elif frm in special_welcome_messages:
        welcome_message = special_welcome_messages[frm]
    else:
        welcome_message = f"🚾 مرحبا بك في الغرفة 🚾\n🆔 : {frm}\n👑 : {role_str}"

    await send_group_msg(ws, room, welcome_message)


# Daftar pesan perpisahan dengan variasi emotikon "bye"
MsgULeave = [
    "{} مع السلامة 👋",
    "{} راح الححلو 😢",
    "{} بحفظ ربي 🙋",
    "{} الله معاك 🖐",
    "{} ذهب كالنجوم 🌟",
    "{} بقبر 😇",
    "{} بحفرة 🥹",
    "{} روحة بلا ردة 👻",
]

async def left_user_msg(ws, data):
    if not msg_leave_enabled:
        return
    room = data['name']
    frm = data['username']
    
    # Pilih pesan perpisahan dengan variasi emotikon "bye"
    msg_wc = random.choice(MsgULeave).format(frm)
    await asyncio.sleep(0) 
    await send_group_msg(ws, room, msg_wc)

   
   
async def ban_user(ws, room, target_username, reason=""):
    jsonbody = {
        "handler": "room_admin",
        "type": "change_role",
        "id": gen_random_str(20),
        "room": room,
        "t_username": target_username,
        "t_role": "outcast"
    }
    await ws.send(json.dumps(jsonbody))
    if reason:
        await send_pvt_msg(ws, target_username, 
        f"You have been banned from\n"
        f"🏠 : {room}\n"
        f"📝 : {reason}")
        await send_group_msg(ws, room,
        f"🚫 {target_username} has been banned\n"
        f"🛑 ID blacklisted"
        )
    else:
        await send_pvt_msg(ws, target_username, f"You have been banned from {room}")


async def kick_user(ws, room, target_username, reason=""):
    jsonbody = {
        "handler": "room_admin",
        "type": "kick",
        "room": room,
        "t_username": target_username,
    }
    if reason:
        await send_pvt_msg(ws, target_username,
        f"You have been kicked from\n"
        f"🏠 : {room}\n"
        f"📝 : {reason}")
    else:
        await send_pvt_msg(ws, target_username, f"You have been kicked from {room}")
    
    await ws.send(json.dumps(jsonbody))
    if reason:
        await send_group_msg(ws, room,
        f"{target_username} has been kicked\n"
        f"reason : {reason}")



def gen_random_str(length):
    return ''.join(random.choice(ALLOWED_CHARS) for i in range(length))


def main():
    init_db()  # Inisialisasi database


async def start_bot():
    websocket = await websockets.connect(SOCKET_URL, ssl=True)
    await login(websocket)
    
    # Mulai pengingat jam
    asyncio.create_task(send_hourly_reminder(websocket))
   
    
    auto_post_task = asyncio.create_task(auto_post_message(websocket, GROUP_TO_INIT_JOIN, "🛡️ coded by saheer 🛡️"))

    while True:
        if not websocket.open:
            try:
                print('Websocket is NOT connected. Reconnecting...')
                websocket = await websockets.connect(SOCKET_URL, ssl=True)
                await login(websocket)
            except:
                print('Unable to reconnect, trying again.')

        try:
            async for payload in websocket:
                if payload is not None:
                    data = json.loads(payload)
                    handler = data[HANDLER]

                    if handler == HANDLER_LOGIN_EVENT and data[TYPE] == EVENT_TYPE_SUCCESS:
                        print("LOGGED IN SUCCESS")
                        
                        
                        await join_group(websocket, GROUP_TO_INIT_JOIN)

                        # await set_status(websocket, random.choice(dstatus))
                        await set_status(websocket, dstatus)
                    elif handler == "friend_requests":
                        await cid_add(websocket, data)
                        # Logika untuk penanganan login berhasil
                        # pass

                    elif handler == HANDLER_ROOM_EVENT and data[TYPE] == MSG_TYPE_TXT:
                        # Penanganan pesan grup
                        await on_message(websocket, data)

                    # wc_user_msg
                    elif handler == HANDLER_ROOM_EVENT and data[TYPE] == "user_joined":
                        await wc_user_msg(websocket, data)
                        
                        
                        # left_user_msg
                    elif handler == HANDLER_ROOM_EVENT and data[TYPE] == "user_left":
                        await left_user_msg(websocket, data)

                    
                    # profile_msg
                    if handler == HANDLER_PROFILE_OTHER:
                        views = data['views']
                        userId = data['user_id']
                        userName = data["type"]
                        status = remove_html_tags(data.get('status', 'N/A'))
                        status = remove_html_tags(data['status'])
                        gender = data['gender']
                        genderStr = ""
                        if gender == "1":
                            genderStr = "♂️ Male"
                        elif gender == "2":
                            genderStr = "♀️ Female"
                        else:
                            genderStr = "❓ Not defined"
                        
                        friendsCount = data["roster_count"]
                        regDate = data["reg_date"]
                        merchant = data["is_merchant"]
                        merchantStr = ""
                        if merchant == "0":
                            merchantStr = "❌ No"
                        elif merchant == "1":
                            merchantStr = "✅ Yes"
                        else:
                            merchantStr = "❓ Not defined"
                        agent = data["is_agent"]
                        agentStr = ""
                        if agent == "0":
                            agentStr = "❌ No"
                        elif agent == "1":
                            agentStr = "✅ Yes"
                        else:
                            agentStr = "❓ Not defined"
                        country = data["country"]
                        sent_gifts = data['sent_gifts']
                        received_gifts = data['received_gifts']
                        profile_msg = f"👤 User ID : {userId}\n📛 Username : {userName}\n💬 Status : {status}\n🚻 Gender : {genderStr}\n👥 Friends : {friendsCount}\n🛒 Is Merchant : {merchantStr}\n🎯 Is Agent : {agentStr}\n🌍 Country : {country}\n📸\n📅 User Since : {regDate}\n👁️ Views : {views}\n🎁 Sent Gifts : {sent_gifts}\n🎉 Received Gifts : {received_gifts}"
                        
                        if photo:
                            await send_group_msg_image(websocket, tempRoom, photo)
                        else:
                            await send_group_msg(websocket, tempRoom, "❗ No Photo Found")
                        await send_group_msg(websocket, tempRoom, profile_msg)

                    elif handler == HANDLER_CHAT_MESSAGE and data[TYPE] == MSG_TYPE_TXT:
                        
                        # Penanganan pesan pribadi
                        await on_private_message(websocket, data)
                        
                        await on_user_joined(websocket, data)

        except Exception as e:
            print(f'Error receiving message from websocket : {str(e)}')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    loop.run_forever()