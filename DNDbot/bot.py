from twitchAPI.twitch import Twitch 
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatCommand
from retrying import retry
from dotenv import load_dotenv
import asyncio
import openai
import tokenCounter
import cleanUp
import rules
import pix
import os

load_dotenv()

openai.api_key = os.environ['API_KEY']

class dndGPT:
    def __init__(self, app_id, app_secret, user_scope, target_channel, bot_name):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_scope = user_scope
        self.target_channel = target_channel
        self.bot = '@' + bot_name
        self.twitch = None
        self.chat = None
        self.conversation = [{"role": "system", "content": rules.personality}]
        self.initial_gametimer = rules.game_time
        self.max_gametimer = self.initial_gametimer
        self.messagetimer = rules.response_time
        self.countdown_game_task = None
        self.countdown_message_task = None
        self.is_ending = False
        self.is_running = False
        self.has_user_responded = False


    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def create_prompt(self, prompt, command=False):
        print('[communicating with chatGPT API, please wait]')
        return openai.chat.completions.create(model='gpt-3.5-turbo', messages=self.conversation, temperature=1.2)


    async def on_ready(self, ready_event: EventData):
        print('dndGPT has joined')
        await ready_event.chat.join_room(self.target_channel)
    

    async def start_game(self):
        self.is_ending = False 
        self.gametimer = self.initial_gametimer  
        self.max_gametimer = self.initial_gametimer
        self.messagetimer = rules.response_time
        try:
            completion = self.create_prompt(rules.personality)
            self.conversation.append({"role": "assistant", "content": completion.choices[0].message.content})
            response_parts = cleanUp.split_response(completion.choices[0].message.content)
            for part in response_parts:
                part = cleanUp.ascii_sanitize(part)
                print(part)
                await self.chat.send_message(self.target_channel, f'{part}')
                await asyncio.sleep(3)
            if rules.image_gen: await pix.make_picture(response_parts[0])
            if rules.intro_message: await self.chat.send_message(self.target_channel, rules.intro_message)
        except Exception as e:
                print('An error occurred: ', e)
        self.countdown_game_task = asyncio.create_task(self.countdown_game())
        self.countdown_message_task = asyncio.create_task(self.countdown_message())
        self.is_running = True
        self.has_user_responded = False


    async def start_session(self, cmd:ChatCommand = None):
        if self.countdown_game_task is not None:
            self.countdown_game_task.cancel()
        if self.countdown_message_task is not None:
            self.countdown_message_task.cancel()
        if cmd and cmd.user.name.lower() in rules.users:
            await self.start_game()
        elif not cmd:
            await self.start_game()


    async def end_session(self, cmd:ChatCommand = None):
        if not self.is_running:
            return
        self.is_ending = True
        self.limit_conversation_tokens()
        reason = 'The DND session is concluded. In less than 60 words please come up with a brief conclusion from where we are at in the story currently.'
        self.conversation.append({"role": "user", "content": reason})
        try:
            completion = self.create_prompt('The DND session is concluded. In less than 60 words please come up with a brief conclusion from where we are at in the story currently.')
            self.conversation.append({"role": "assistant", "content": completion.choices[0].message.content})
            response_parts = cleanUp.split_response(completion.choices[0].message.content)
            for part in response_parts:
                part = cleanUp.ascii_sanitize(part)
                print(part)
                await self.chat.send_message(self.target_channel, f'{part}')
                await asyncio.sleep(3)
            if rules.image_gen: await pix.make_picture(response_parts[0])
        except Exception as e:
            print('An error occurred: ', e)
        if self.countdown_message_task is not None:
            self.countdown_message_task.cancel()
        if self.countdown_game_task is not None:
            self.countdown_game_task.cancel()
        self.conversation = [{"role": "system", "content": rules.personality}]
        self.is_running = False
        if rules.interval:
            print(f'Next DND sesh set to begin in {rules.interval / 60} minutes!')
            self.interval_task = asyncio.create_task(self.start_interval_timer())
        self.has_user_responded = False

    async def progress_session(self, cmd:ChatCommand = None):
        if self.is_ending:
            return
        if not self.is_running:
            return
        self.limit_conversation_tokens()
        reason = 'Please progress the story in less than 60 words'
        self.conversation.append({"role": "user", "content": reason})
        try:
            completion = self.create_prompt(reason)
            self.conversation.append({"role": "assistant", "content": completion.choices[0].message.content})
            response_parts = cleanUp.split_response(completion.choices[0].message.content)
            for part in response_parts:
                part = cleanUp.ascii_sanitize(part)
                print(part)
                await self.chat.send_message(self.target_channel, f'{part}')
                await asyncio.sleep(3)
            if rules.image_gen: await pix.make_picture(response_parts[0])
        except Exception as e:
            print('An error occurred: ', e)
        self.messagetimer = rules.response_time
        if self.countdown_message_task is not None:
            self.countdown_message_task.cancel()
        self.countdown_message_task = asyncio.create_task(self.countdown_message())
        self.has_user_responded = False
        self.max_gametimer -= rules.response_time
        print(f'reducing total game time by {rules.response_time} since there was no response')


    async def start_interval_timer(self):
        if rules.interval > 0:
            await asyncio.sleep(rules.interval)
            if not self.is_running:
                await self.start_session()


    async def countdown_game(self):
        while not self.is_ending:
            self.gametimer -= 1
            if self.gametimer % 10 == 0: print(f'Game time remaining: {self.gametimer}')
            if self.gametimer <= 0:
                print('Game time is up, ending the game!')
                await self.end_session()
            await asyncio.sleep(1)
        

    async def countdown_message(self):
        while not self.is_ending:
            self.messagetimer -= 1
            if self.messagetimer % 10 == 0: print(f'Player time to respond: {self.messagetimer}')
            if self.messagetimer <= 0:
                print('Response time is up, progressing the game')
                await self.progress_session()
            await asyncio.sleep(1)


    async def on_message(self, msg: ChatMessage):
        print(f'in {msg.room.name}, {msg.user.name} said: {msg.text}')
        message = msg.text.lower().split()
        if self.bot in message and self.is_running:
            print('responding to a convo with, ', {msg.user.name})
            prompt = msg.text.replace(self.bot, '').strip()
            self.limit_conversation_tokens()
            self.conversation.append({"role": "user", "content": msg.user.name + ' -- ' + msg.text})
            print('total tokens:', tokenCounter.num_tokens_from_messages(self.conversation))
            try:
                completion = self.create_prompt(prompt)
                self.conversation.append({"role": "assistant", "content": completion.choices[0].message.content})
                response_parts = cleanUp.split_response(completion.choices[0].message.content)
                for part in response_parts:
                    part = cleanUp.ascii_sanitize(part)
                    print(part)
                    await self.chat.send_message(self.target_channel, f'{part}')
                    await asyncio.sleep(5)
                if rules.image_gen: await pix.make_picture(response_parts[0])
            except Exception as e:
                print('An error occurred: ', e)
            self.messagetimer = rules.response_time
            if self.countdown_message_task is not None:
                self.countdown_message_task.cancel()
            self.countdown_message_task = asyncio.create_task(self.countdown_message())
            self.has_user_responded = True
            if self.has_user_responded:
                self.gametimer = min(self.max_gametimer, self.gametimer + rules.response_time)

    
    def limit_conversation_tokens(self):
        while tokenCounter.num_tokens_from_messages(self.conversation) > 3800:
            if len(self.conversation) > 2:
                print('memory decay -- removing older messages')
                self.conversation.pop(2)
                self.conversation.pop(2)
            else:
                print('Only the initial system message remains, but it exceeds the token limit.')
                break


    async def run(self):
        self.twitch = await Twitch(self.app_id, self.app_secret)
        auth = UserAuthenticator(self.twitch, self.user_scope)
        token, refresh_token = await auth.authenticate()
        await self.twitch.set_user_authentication(token, self.user_scope, refresh_token)
        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.register_event(ChatEvent.MESSAGE, self.on_message)
        self.chat.register_command(rules.start, self.start_session)
        self.chat.register_command(rules.end, self.end_session)
        self.chat.register_command(rules.progress, self.progress_session)
        self.chat.start()

        try:
            input('press ENTER to stop\n')
        finally:
            self.chat.stop()
            await self.twitch.close()


if __name__ == '__main__':
    APP_ID = os.environ['APP_ID']
    APP_SECRET = os.environ['APP_SECRET'] 
    USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
    TARGET_CHANNEL = rules.channel
    BOT_NAME = rules.botname

    gptexe = dndGPT(APP_ID, APP_SECRET, USER_SCOPE, TARGET_CHANNEL, BOT_NAME)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gptexe.run())
        loop.close()
    except Exception as e:
        print("Exception in main loop: ", e)
