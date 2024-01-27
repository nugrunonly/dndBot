# who should the bot listen to
users = ['nugrun_exe', 'nugrunonly']

# who's channel should the bot join
channel = 'nugrunonly'

# what name should the boot look for to respond to messages
botname = 'nugrun_exe'

# commands name to control dnd sesh manually (don't use a '!' -- it automatically looks for that)
start = 'start'
end = 'end'
progress = 'go'

# time in seconds someone has to respond before moving on (default 90)
response_time = 90

# minimum time in seconds the game will run (recommended this be twice the length of the response time -- default 180)
game_time = 180 

# time in seconds that the game will automatically restart after last game ended.
# 0 = never run automatically, 3600 = run once per hour
interval = 0

#this will post after the start of the campaign after the first messages -- leave blank if no message desired
intro_message = '(@me to participate in this campaign)'

#do you want it to also make pictures? (costs more money) yes = True, no = False
image_gen = True

#dont fuck with this
personality = 'You are a Dungeon Master for Dungeons and Dragons. Please keep your responses brief with less than 60 words total. Begin by creating a short campaign. Each time someone responds you will act as the DM and make decisions based on the current context. Try to keep the story progressing towards a conclusion.'
