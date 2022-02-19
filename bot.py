# (c) @Emin (eGi)
# Edit codes at your own risk
from config import Config
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
import random
import asyncio
from helper.db import manage_db
from pyrogram.errors import UserNotParticipant
from helper.markup import MakeCaptchaMarkup
from helper.captcha_maker import number_, emoji_


# Prepare bot
app = Client(Config.SESSION_NAME, api_id=Config.APP_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
# Local database for saving user info
LocalDB = {}
ch_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text="Developer", url="https://t.me/b4f2f"),
                                    InlineKeyboardButton(text="Blog", url="https://t.me/eGiblog")]])


@app.on_chat_member_updated()
async def check_chat_captcha(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat = manage_db().chat_in_db(chat_id)
    if not chat:
        return
    try:
        user_s = await client.get_chat_member(chat_id, user_id)
        if (user_s.is_member is False) and (LocalDB.get(user_id, None) is not None):
            try:
                await client.delete_messages(
                    chat_id=chat_id,
                    message_ids=LocalDB[user_id]["msg_id"]
                )
            except:
                pass
            return
        elif (user_s.is_member is False):
            return
    except UserNotParticipant:
        return
    chat_member = await client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
        if chat_member.restricted_by.id == (await client.get_me()).id:
            pass
        else:
            return
    try:
        if LocalDB.get(user_id, None) is not None:
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text=f"{message.from_user.mention} Doğrulamadan tekrar grupa katılfı!\n\n"
                         f"10 dakika sonra tekrar deniye bilir.",
                    disable_web_page_preview=True
                )
                await client.delete_messages(chat_id=chat_id,
                                             message_ids=LocalDB[user_id]["msg_id"])
            except:
                pass
            await asyncio.sleep(600)
            del LocalDB[user_id]
    except:
        pass
    try:
        await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
    except:
        return
    await client.send_message(chat_id,
                              text=f"{message.from_user.mention} Burada sohbet etmek için lütfen insan olduğunuzu doğrulayın",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Şimdi Doğrulayın", callback_data=f"verify_{chat_id}_{user_id}")]]))
        
@app.on_message(filters.command(["captcha"]) & ~filters.private)
async def add_chat(bot, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user = await bot.get_chat_member(chat_id, user_id)
    if user.status == "creator" or user.status == "administrator" or user.user.id in Config.SUDO_USERS:
        chat = manage_db().chat_in_db(chat_id)
        if chat:
            await message.reply_text("Captcha zaten burada açık, açmak için /remove komutunu kullanın")
        else:
            await message.reply_text(text=f"Lütfen captcha türünü seçin",
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Numara", callback_data=f"new_{chat_id}_{user_id}_N"),
                                                                        InlineKeyboardButton(text="Emoji", callback_data=f"new_{chat_id}_{user_id}_E")]]))
        
@app.on_message(filters.command(["help"]))
async def start_chat(bot, message):
    await message.reply_text(text="/captcha - aç : 2 türlü captcha vardır\n/remove - captcha kapat\n\ndaha fazla yardım için developere yaza bilirsiniz",
                             reply_markup=ch_markup)
    
@app.on_message(filters.command(["start"]))
async def help_chat(bot, message):
    await message.reply_text(text="Beni kullanarak sizin grupunuzu botlardan koruya bilirim.\n\nDaha fazla bilgi için /help kullanın.",
                             reply_markup=ch_markup)
    
@app.on_message(filters.command(["remove"]) & ~filters.private)
async def del_chat(bot, message):
    chat_id = message.chat.id
    user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user.status == "creator" or user.status == "administrator" or user.user.id in Config.SUDO_USERS:
        j = manage_db().delete_chat(chat_id)
        if j:
            await message.reply_text("Bu sohbette captcha kapatıldı")
        
@app.on_callback_query()
async def cb_handler(bot, query):
    cb_data = query.data
    if cb_data.startswith("new_"):
        chat_id = query.data.rsplit("_")[1]
        user_id = query.data.split("_")[2]
        captcha = query.data.split("_")[3]
        if query.from_user.id != int(user_id):
            await query.answer("Bu mesaj sana değil", show_alert=True)
            return
        if captcha == "N":
            type_ = "Numara"
        elif captcha == "E":
            type_ = "Emoji"
        chk = manage_db().add_chat(int(chat_id), captcha)
        if chk == 404:
            await query.message.edit("Captcha zaten burada açık, kapatmak için /remove kullanın")
            return
        else:
            await query.message.edit(f"{type_} Bu sohbet için captcha açıldı.")
    elif cb_data.startswith("verify_"):
        chat_id = query.data.split("_")[1]
        user_id = query.data.split("_")[2]
        if query.from_user.id != int(user_id):
            await query.answer("Bu mesaj sana değil!", show_alert=True)
            return
        chat = manage_db().chat_in_db(int(chat_id))
        print("proccesing cb data")
        if chat:
            c = chat["captcha"]
            markup = [[],[],[]]
            if c == "N":
                print("proccesing number captcha")
                await query.answer("Creating captcha for you")
                data_ = number_()
                _numbers = data_["answer"]
                list_ = ["0","1","2","3","5","6","7","8","9"]
                random.shuffle(list_)
                tot = 2
                LocalDB[int(user_id)] = {"answer": _numbers, "list": list_, "mistakes": 0, "captcha": "N", "total":tot, "msg_id": None}
                count = 0
                for i in range(3):
                    markup[0].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(3):
                    markup[1].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(3):
                    markup[2].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
            elif c == "E":
                print("proccesing img captcha")
                await query.answer("Creating captcha for you")
                data_ = emoji_()
                _numbers = data_["answer"]
                list_ = data_["list"]
                count = 0
                tot = 3
                for i in range(5):
                    markup[0].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(5):
                    markup[1].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                for i in range(5):
                    markup[2].append(InlineKeyboardButton(f"{list_[count]}", callback_data=f"jv_{chat_id}_{user_id}_{list_[count]}"))
                    count += 1
                LocalDB[int(user_id)] = {"answer": _numbers, "list": list_, "mistakes": 0, "captcha": "E", "total":tot, "msg_id": None}
            c = LocalDB[query.from_user.id]['captcha']
            if c == "N":
                typ_ = "numara"
            if c == "E":
                typ_ = "emoji"
            msg = await bot.send_photo(chat_id=chat_id,
                            photo=data_["captcha"],
                            caption=f"{query.from_user.mention} Lütfen her birine tıklayın {typ_} Resimde gösterilen buton, {tot} hatalara izin verilir.",
                            reply_markup=InlineKeyboardMarkup(markup))
            LocalDB[query.from_user.id]['msg_id'] = msg.message_id
            await query.message.delete()
    if cb_data.startswith("jv_"):
        chat_id = query.data.rsplit("_")[1]
        user_id = query.data.split("_")[2]
        _number = query.data.split("_")[3]
        if query.from_user.id != int(user_id):
            await query.answer("Bu mesaj sana değil!", show_alert=True)
            return
        if query.from_user.id not in LocalDB:
            await query.answer("Yeniden katıldıktan sonta tekrar deneyin!", show_alert=True)
            return
        c = LocalDB[query.from_user.id]['captcha']
        tot = LocalDB[query.from_user.id]["total"]
        if c == "N":
            typ_ = "numara"
        if c == "E":
            typ_ = "emoji"
        if _number not in LocalDB[query.from_user.id]["answer"]:
            LocalDB[query.from_user.id]["mistakes"] += 1
            await query.answer(f"Yanlış bastın {typ_}!", show_alert=True)
            n = tot - LocalDB[query.from_user.id]['mistakes']
            if n == 0:
                await query.message.edit_caption(f"{query.from_user.mention}, captchayı çözemedin!\n\n"
                                               f"10 dakika sonra tekrar deneyin.",
                                               reply_markup=None)
                await asyncio.sleep(600)
                del LocalDB[query.from_user.id]
                return
            markup = MakeCaptchaMarkup(query.message["reply_markup"]["inline_keyboard"], _number, "❌")
            await query.message.edit_caption(f"{query.from_user.mention}, Resimde gördüğünüz {typ_}s tüm seçin. "
                                           f"Yalnızca  {n} hataya izin verilir.",
                                           reply_markup=InlineKeyboardMarkup(markup))
        else:
            LocalDB[query.from_user.id]["answer"].remove(_number)
            markup = MakeCaptchaMarkup(query.message["reply_markup"]["inline_keyboard"], _number, "✅")
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(markup))
            if not LocalDB[query.from_user.id]["answer"]:
                await query.answer("🥳 Captcahyı geçtin!", show_alert=True)
                del LocalDB[query.from_user.id]
                await bot.unban_chat_member(chat_id=query.message.chat.id, user_id=query.from_user.id)
                await query.message.delete(True)
            await query.answer()
    elif cb_data.startswith("done_"):
        await query.answer("Aynı düğmeye tekrar tıklamayın", show_alert=True)
    elif cb_data.startswith("wrong_"):
        await query.answer("Aynı düğmeye tekrar tıklamayın", show_alert=True)
        
if __name__ == "__main__":
    app.run()
