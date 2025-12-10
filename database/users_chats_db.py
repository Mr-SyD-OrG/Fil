# https://github.com/odysseusmax/animated-lamp/blob/master/bot/database/database.py
import motor.motor_asyncio
from info import DATABASE_NAME, DATABASE_URI, IMDB, IMDB_TEMPLATE, MELCOW_NEW_USERS, P_TTI_SHOW_OFF, SINGLE_BUTTON, SPELL_CHECK_REPLY, PROTECT_CONTENT, AUTO_DELETE, MAX_BTN, AUTO_FFILTER, SHORTLINK_API, SHORTLINK_URL, IS_SHORTLINK, TUTORIAL, CLONE_DB_URI, IS_TUTORIAL
import datetime, re
import pytz
from info import DATABASE_URI as MONGO_URI
from pymongo import MongoClient
import dateparser
import time

my_client = MongoClient(MONGO_URI)
mydb = my_client["referal_user"]

async def referal_add_user(user_id, ref_user_id):
    user_db = mydb[str(user_id)]
    user = {'_id': ref_user_id}
    try:
        user_db.insert_one(user)
        return True
    except DuplicateKeyError:
        return False
    

async def get_referal_all_users(user_id):
    user_db = mydb[str(user_id)]
    return user_db.find()
    
async def get_referal_users_count(user_id):
    user_db = mydb[str(user_id)]
    count = user_db.count_documents({})
    return count
    

async def delete_all_referal_users(user_id):
    user_db = mydb[str(user_id)]
    user_db.delete_many({}) 
class Database:
    
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.users = self.db.uersz
        self.req = self.db.requests
        self.syd = self.db.bots
        self.all = self.db.filed
        self.words = self.db.words
        self.chnl = self.db.chnl
        self.filters = self.db.filters


# ---------------------- Filter Methods ----------------------
    async def create_filter_doc(self, chat_id, trigger, response_text="", button_text=None, button_url=None, photo_file_id=None):
        doc = {
            "chat_id": chat_id,
            "trigger": trigger,
            "response_text": response_text,
            "button_text": button_text,
            "button_url": button_url,
            "photo_file_id": photo_file_id,
        }
        res = await self.filters.insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc


    async def get_filter(self, chat_id, trigger):
        return await self.filters.find_one({"chat_id": chat_id, "trigger": trigger})


    async def delete_filter(self, chat_id, trigger):
        return await self.filters.delete_one({"chat_id": chat_id, "trigger": trigger})


    async def delete_all_filters(self, chat_id):
        return await self.filters.delete_many({"chat_id": chat_id})

    async def update_filter(self, chat_id, trigger, update):
        return await self.filters.update_one({"chat_id": chat_id, "trigger": trigger}, {"$set": update})

    async def set_channels(self, user_id: int, channel_ids):
        """
        Overwrite user's channel list.
        - channel_ids: single int or list/tuple of int
        - Completely removes old channel list and sets new one
        """

        # Convert single value to list
        if isinstance(channel_ids, int):
            channel_ids = [channel_ids]

        await self.chnl.update_one(
            {"_id": user_id},
            {"$set": {"channels": channel_ids}},
            upsert=True
        )

    async def get_channels(self, user_id: int):
        doc = await self.chnl.find_one({"_id": user_id})
        return doc.get("channels", []) if doc else []

    async def delete_user(self, user_id: int):
        await self.chnl.delete_one({"_id": user_id})

    async def clear_all(self):
        """Drop entire collection."""
        await self.chnl.drop()
        
    async def find_join_req(self, user_id: int, channel_id: int):
        doc = await self.req.find_one({'user_id': user_id, 'channel_id': channel_id})
        return bool(doc)

    async def update_count(self, user_id: int, new_count: int):
        await self.req.update_one(
            {"_id": user_id},
            {"$set": {"count": new_count}}
        )
    
    async def syd_user(self, user_id: int):
        return await self.req.find_one({"_id": user_id})
    

    async def add_join_oreq(self, user_id: int, channel_id: int):
        await self.req.update_one(
            {'user_id': user_id, 'channel_id': channel_id},
            {'$set': {'user_id': user_id, 'channel_id': channel_id}},
            upsert=True
        )

    async def add_join_req(self, user_id: int, channel_id: int):
    # Add the channel ONLY if it's not already in the array
        result = await self.req.update_one(
            {"_id": user_id},
            {
                "$addToSet": {"channels": channel_id},
                "$setOnInsert": {"time": int(time.time())},   # only on first user document creation
            },
            upsert=True
        )

        if result.modified_count == 1:
            await self.req.update_one(
                {"_id": user_id},
                {"$set": {
                    "time": int(time.time()),   # reset time
                    "count": 0                  # reset count
                }}
            )
            
    async def del_join_req(self, user_id: int, channel_id: int):
        await self.req.delete_one({'user_id': user_id, 'channel_id': channel_id})

    async def delete_channel_users(self, channel_id: int):
        result = await self.req.delete_many({"channel_id": channel_id})
        return result.deleted_count
        
    async def del_all_join_req(self):
        await self.req.drop()
        
    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )


    def new_group(self, id, title):
        return dict(
            id = id,
            title = title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})
    

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})


    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        chats = self.grp.find({'chat_status.is_disabled': True})
        b_chats = [chat['id'] async for chat in chats]
        b_users = [user['id'] async for user in users]
        return b_users, b_chats
    

    async def add_word(self, phrase: str, expire_text: str):
        phrase = phrase.lower().strip()
        expire_time = dateparser.parse(expire_text)
        if not expire_time:
            return "invalid_date"
        await self.words.insert_one({
            "word": phrase,
            "expireAt": expire_time
        })
        return True

    async def check_word_exists(self, text: str):
        text = text.lower()
        now = datetime.datetime.now(pytz.timezone("Asia/Kolkata")).replace(tzinfo=None)
        cursor = self.words.find({})
        async for doc in cursor:
            # Remove expired word
            
            if "expireAt" in doc and doc["expireAt"] < now:
                await self.words.delete_one({"word": doc["word"]})
                continue
            if doc["word"] in text:
                return True
        return False


    async def get_all_words(self):
        cursor = self.words.find({})
        return [doc["word"] async for doc in cursor]

    async def delete_word(self, word: str):
        result = await self.words.delete_one({"word": word.lower().strip()})
        return result.deleted_count > 0

    async def add_chat(self, chat, title):
        chat = self.new_group(chat, title)
        await self.grp.insert_one(chat)
    

    async def get_chat(self, chat):
        chat = await selfrequests
        d_one({'id':int(chat)})
        return False if not chat else chat.get('chat_status')
    


    async def remove_stored_file_id(self, user_id: int):
        await self.all.delete_one({"_id": user_id})

    async def store_file_id_if_not_subscribed(self, user_id: int, file_id: str, mess: int):
        await self.all.update_one(
            {"_id": user_id},
            {"$set": {"file_id": file_id, "mess": mess}},
            upsert=True
        )
    async def get_stored_file_id(self, user_id: int) -> dict | None:
        return await self.all.find_one({"_id": user_id})
        
    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}})
        
    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}})
        
    
    async def get_settings(self, id):
        default = {
            'button': SINGLE_BUTTON,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'auto_delete': AUTO_DELETE,
            'auto_ffilter': AUTO_FFILTER,
            'max_btn': MAX_BTN,
            'template': IMDB_TEMPLATE,
            'shortlink': SHORTLINK_URL,
            'shortlink_api': SHORTLINK_API,
            'is_shortlink': IS_SHORTLINK,
            'tutorial': TUTORIAL,
            'is_tutorial': IS_TUTORIAL
        }
        chat = await self.grp.find_one({'id':int(id)})
        if chat:
            return chat.get('settings', default)
        return default
    
    async def disable_chat(self, chat, reason="No Reason"):
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat)}, {'$set': {'chat_status': chat_status}})
    

    async def total_chat_count(self):
        count = await self.grp.count_documents({})
        return count
   
    async def get_all_chats(self):
        return self.grp.find({})
        
    async def add_bot(self, user_id: int, bot_id: int, token, name, username):
       bot = await self.in_bot(user_id, bot_id)
       if bot:
         return False
       return await self.syd.insert_one({"user_id": user_id, "bot_id": bot_id, "token": token, "name": name, "username": username})

    async def in_bot(self, user_id: int, bot_id: int) -> bool:
       bot = await self.syd.find_one({"user_id": int(user_id), "bot_id": int(bot_id)})
       return bool(bot)

    async def remove_bot(self, user_id: int, bot_id: int):
       bot = await self.in_bot(user_id, bot_id )
       if not bot:
         return False
       return await self.syd.delete_many({"user_id": int(user_id), "bot_id": int(bot_id)})
    
    async def get_bots(self, user_id: int):
       bots = self.syd.find({"user_id": int(user_id)})
       return [bot async for bot in bots]

    async def get_bot(self, user_id: int, bot_id: int):
       return await self.syd.find_one({"user_id": int(user_id), "bot_id": int(bot_id)})
       
    async def get_setings(self, user_id, bot_id):
        default = {
            'forc_id': AUTH_CHANNEL,
            'botpm': P_TTI_SHOW_OFF,
            'file_secure': PROTECT_CONTENT,
            'imdb': IMDB,
            'spell_check': SPELL_CHECK_REPLY,
            'welcome': MELCOW_NEW_USERS,
            'auto_delete': AUTO_DELETE,
            'auto_ffilter': AUTO_FFILTER,
            'max_btn': MAX_BTN,
            'template': IMDB_TEMPLATE,
            'shortlink': SHORTLINK_URL,
            'shortlink_api': SHORTLINK_API,
            'is_shortlink': IS_SHORTLINK,
            'tutorial': TUTORIAL,
            'is_tutorial': IS_TUTORIAL
        }
        bot = await self.syd.find_one({'user_id':int(id), 'bot_id':int(bot_id)})
        if bot:
            return bot.get('setings', default)
        return default

    async def update_setings(self, user_id, bot_id, settings):
        await self.syd.update_one(
            {'user_id': int(user_id), 'bot_id': int(bot_id)},  # Added bot_id to the query
            {'$set': {'setings': setings}}
        )

    async def get_db_size(self):
        return (await self.db.command("dbstats"))['dataSize']

    
    async def get_user(self, user_id):
        user_data = await self.users.find_one({"id": user_id})
        return user_data
    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def has_premium_access(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            expiry_time = user_data.get("expiry_time")
            if expiry_time is None:
                # User previously used the free trial, but it has ended.
                return False
            elif isinstance(expiry_time, datetime.datetime) and datetime.datetime.now() <= expiry_time:
                return True
            else:
                await self.users.update_one({"id": user_id}, {"$set": {"expiry_time": None}})
        return False
        
    async def update_user(self, user_data):
        await self.users.update_one({"id": user_data["id"]}, {"$set": user_data}, upsert=True)

    async def update_one(self, filter_query, update_data):
        try:
            # Assuming self.client and self.users are set up properly
            result = await self.users.update_one(filter_query, update_data)
            return result.matched_count == 1
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    async def get_expired(self, current_time):
        expired_users = []
        if data := self.users.find({"expiry_time": {"$lt": current_time}}):
            async for user in data:
                expired_users.append(user)
        return expired_users

    async def remove_premium_access(self, user_id):
        return await self.update_one(
            {"id": user_id}, {"$set": {"expiry_time": None}}
        )

    async def check_trial_status(self, user_id):
        user_data = await self.get_user(user_id)
        if user_data:
            return user_data.get("has_free_trial", False)
        return False

    async def give_free_trial(self, user_id):
        #await set_free_trial_status(user_id)
        user_id = user_id
        seconds = 8*60         
        expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        user_data = {"id": user_id, "expiry_time": expiry_time, "has_free_trial": True}
        await self.users.update_one({"id": user_id}, {"$set": user_data}, upsert=True)

class Dab:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.grp = self.db.groups
        self.users = self.db.uersz
        self.req = self.db.requests
        
    async def find_join_req(self, id):
        return bool(await self.req.find_one({'id': id}))
        
    async def add_join_req(self, id):
        await self.req.insert_one({'id': id})
    async def del_join_req(self):
        await self.req.drop()

    
db = Database(DATABASE_URI, DATABASE_NAME)
bd = None #Dab(CLONE_DB_URI, DATABASE_NAME)
