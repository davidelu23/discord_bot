#!./.venv/bin/python
from sqlite3 import connect
from types import NoneType

import discord  # base discord module
import code  # code.interact
import os  # environment variables
import inspect  # call stack inspection
import random  # dumb random number generator
from pytube import YouTube
from googleapiclient.discovery import build

from discord import VoiceChannel
from discord.ext import commands  # Bot class and utils


################################################################################
############################### HELPER FUNCTIONS ###############################
################################################################################

# log_msg - fancy print
#   @msg   : string to print
#   @level : log level from {'debug', 'info', 'warning', 'error'}
def log_msg(msg: str, level: str):
	# user selectable display config (prompt symbol, color)
	dsp_sel = {
		'debug': ('\033[34m', '-'),
		'info': ('\033[32m', '*'),
		'warning': ('\033[33m', '?'),
		'error': ('\033[31m', '!'),
	}

	# internal ansi codes
	_extra_ansi = {
		'critical': '\033[35m',
		'bold': '\033[1m',
		'unbold': '\033[2m',
		'clear': '\033[0m',
	}

	# get information about call site
	caller = inspect.stack()[1]

	# input sanity check
	if level not in dsp_sel:
		print('%s%s[@] %s:%d %sBad log level: "%s"%s' % \
			  (_extra_ansi['critical'], _extra_ansi['bold'],
			   caller.function, caller.lineno,
			   _extra_ansi['unbold'], level, _extra_ansi['clear']))
		return

	# print the damn message already
	print('%s%s[%s] %s:%d %s%s%s' % \
		  (_extra_ansi['bold'], *dsp_sel[level],
		   caller.function, caller.lineno,
		   _extra_ansi['unbold'], msg, _extra_ansi['clear']))


################################################################################
############################## BOT IMPLEMENTATION ##############################
################################################################################

# bot instantiation
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)


# on_ready - called after connection to server is established
@bot.event
async def on_ready():
	log_msg('logged on as <%s>' % bot.user, 'info')


# on_message - called when a new message is posted to the server
#   @msg : discord.message.Message
@bot.event
async def on_message(msg):
	# filter out our own messages
	if msg.author == bot.user:
		return

	log_msg('message from <%s>: "%s"' % (msg.author, msg.content), 'debug')

	# overriding the default on_message handler blocks commands from executing
	# manually call the bot's command processor on given message
	await bot.process_commands(msg)


# roll - rng chat command
#   @ctx     : command invocation context
#   @max_val : upper bound for number generation (must be at least 1)
@bot.command(brief='Generate random number between 1 and <arg>')
async def roll(ctx, max_val: int):
	# argument sanity check
	if max_val < 1:
		raise Exception('argument <max_val> must be at least 1')

	await ctx.send(random.randint(1, max_val))

# play - play music command
@bot.command(brief='Connect to channel and play music')
async def play(ctx, music_file: str):
	api_key = os.environ['YT_API_KEY']
	voice = ctx.author.voice
	# check if user is connected to a vc
	if voice is None:
		await ctx.send('ERROR: You are not connected to a voice channel')
		return
	if ctx.voice_client is None:
		await voice.channel.connect()
	try:
		# Build the YouTube API client
		youtube = build('youtube', 'v3', developerKey=api_key)

		# Search for videos
		search_result = youtube.search().list(
			q=music_file,
			type='video',
			part='snippet',
			maxResults=1
		).execute()

		# Select the 1st video
		if search_result['items']:
			# Show preview on discord
			video = search_result['items'][0]
			video_id = video['id']['videoId']
			video_title = video['snippet']['title']
			video_url = f"https://www.youtube.com/watch?v={video_id}"
			await ctx.send(f'Now playing\n{video_url}')
			# Download the video
			yt = YouTube(video_url)
			audio_stream = yt.streams.filter(only_audio=True).first()
			file_path = audio_stream.download()
			# Play music
			ctx.voice_client.play(discord.FFmpegPCMAudio(file_path))
		else:
			await ctx.send('No video found')

	except Exception as e:
		await ctx.send(f'ERROR: {str(e)}')

# stop music
@bot.command(brief='Stops the bot from playing music')
async def stop(ctx):
	voice = ctx.voice_client
	# check if the bot is connected to any vc
	if voice is None:
		await ctx.send('ERROR: I am not connected to any voice channel')
		return
	voice.stop()

# disconnect command
@bot.command(brief='Disconnect from channel if alone')
async def disconnect(ctx):
	voice = ctx.voice_client
	# check if the bot is connected to any vc
	if voice is None:
		await ctx.send('ERROR: I am not connected to any voice channel')
		return
	await ctx.send(f'Disconnected from {ctx.voice_client.channel.mention}')
	await voice.disconnect()

# disconnect if alone in vc
@bot.event
async def on_voice_state_update(member, before, after):
	for guild in bot.guilds:
		if guild.voice_client and guild.voice_client.channel:
			bot_channel = guild.voice_client.channel
			if before.channel != after.channel and before.channel == bot_channel:
				if len(bot_channel.members) < 2:
					await guild.voice_client.disconnect()

# roll_error - error handler for the <roll> command
#   @ctx     : command that crashed invocation context
#   @error   : ...
@roll.error
async def roll_error(ctx, error):
	await ctx.send(str(error))


################################################################################
############################# PROGRAM ENTRY POINT ##############################
################################################################################

if __name__ == '__main__':
	# check that token exists in environment
	if 'BOT_TOKEN' not in os.environ:
		log_msg('save your token in the BOT_TOKEN env variable!', 'error')
		exit(-1)

	# launch bot (blocking operation)
	bot.run(os.environ['BOT_TOKEN'])

