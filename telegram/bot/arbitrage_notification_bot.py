import asyncio
import textwrap
import logging
from database.queries import delete_offer_by_id, update_quantity_in_offer_by_id
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import settings

# =============================
#  Logging setup
# =============================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()


# =============================
#  FSM States for offer editing
# =============================
class EditOffer(StatesGroup):
    waiting_for_new_value = State()
    waiting_for_confirmation = State()


# =============================
#  Arbitrage notification
# =============================
async def send_telegram_message(query_result):
    """Sends formatted arbitrage message with action buttons."""
    item = query_result.buy_offer_rel.item
    sell_offer = query_result.sell_offer_rel
    buy_offer = query_result.buy_offer_rel

    sell_link = f"https://t.me/c/{str(settings.trade_group_id)[4:]}/{sell_offer.message.message_group_id}"
    buy_link = f"https://t.me/c/{str(settings.trade_group_id)[4:]}/{buy_offer.message.message_group_id}"
    sell_sender_link = f"https://t.me/{sell_offer.message.sender_username}"
    buy_sender_link = f"https://t.me/{buy_offer.message.sender_username}"

    text = textwrap.dedent(f"""
    🚨🚨  ARBITRAGE FOUND!  🚨🚨

    📦 ITEM INFO
    ━━━━━━━━━━━━━━━━━━━━
    🪙 Name: {item.item_name}
    🏷️ Type: {item.item_type.name}
    ⭐ Grade: {item.item_grade}
    ⌛ Duration: {item.item_duration}

    💰 ARBITRAGE DATA
    ━━━━━━━━━━━━━━━━━━━━
    💵 Currency: {query_result.currency.name}
    📈 Profit (per one): {query_result.profit_for_one}
    💹 Profit (total): {query_result.profit_for_all}
    💰 Total price: {query_result.price_for_all}

    📤 SELL OFFER
    ━━━━━━━━━━━━━━━━━━━━
    🔗 Message: {sell_link}
    👤 Seller: {sell_sender_link}
    💵 Price (per one): {sell_offer.price_for_one}
    📦 Quantity: {sell_offer.quantity}

    📥 BUY OFFER
    ━━━━━━━━━━━━━━━━━━━━
    🔗 Message: {buy_link}
    👤 Buyer: {buy_sender_link}
    💵 Price (per one): {buy_offer.price_for_one}
    📦 Quantity: {buy_offer.quantity}
    """)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑️ Delete BUY", callback_data=f"delete_buy:{buy_offer.id}"),
            InlineKeyboardButton(text="🗑️ Delete SELL", callback_data=f"delete_sell:{sell_offer.id}")
        ],
        [
            InlineKeyboardButton(text="✏️ Edit BUY", callback_data=f"edit_buy:{buy_offer.id}:{buy_offer.quantity}"),
            InlineKeyboardButton(text="✏️ Edit SELL", callback_data=f"edit_sell:{sell_offer.id}:{sell_offer.quantity}")
        ],
        [
            InlineKeyboardButton(text="💣 Delete BOTH", callback_data=f"delete_both:{buy_offer.id}:{sell_offer.id}")
        ]
    ])

    sent_message = await bot.send_message(settings.my_id, text, reply_markup=keyboard)
    logger.info(f"Arbitrage message sent (buy_id={buy_offer.id}, sell_id={sell_offer.id})")
    return sent_message.message_id


# =============================
#  Offer deletion handlers
# =============================
@dp.callback_query(F.data.startswith("delete_"))
async def delete_offer(callback: types.CallbackQuery):
    """Handles delete button press (buy/sell/both)."""
    parts = callback.data.split(":")
    action = parts[0]
    offer_type = action.split("_")[1]

    if offer_type == "both":
        buy_id, sell_id = parts[1], parts[2]
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_delete:both:{buy_id}:{sell_id}:{callback.message.message_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]])
        await callback.message.reply("Confirm deletion of BOTH offers?", reply_markup=confirm_kb)
        await callback.answer()
        return

    offer_id = parts[1]
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_delete:{offer_type}:{offer_id}:{callback.message.message_id}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    ]])
    await callback.message.reply(f"Confirm deletion of {offer_type.upper()} offer?", reply_markup=confirm_kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_delete"))
async def confirm_delete(callback: types.CallbackQuery):
    """Deletes offer(s) from DB after confirmation."""
    parts = callback.data.split(":")
    offer_type = parts[1]

    try:
        if offer_type == "both":
            buy_id, sell_id = int(parts[2]), int(parts[3])
            await delete_offer_by_id(buy_id)
            await delete_offer_by_id(sell_id)
            logger.info(f"Deleted BOTH offers (buy_id={buy_id}, sell_id={sell_id})")
            await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=int(parts[4]),
                                        text="🚨🚨  ARBITRAGE DELETED!  🚨🚨\n\n💥 BOTH OFFERS DELETED")
        else:
            offer_id = int(parts[2])
            await delete_offer_by_id(offer_id)
            logger.info(f"Deleted {offer_type.upper()} offer (id={offer_id})")
            await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=int(parts[3]),
                                        text=f"🚨🚨  ARBITRAGE DELETED!  🚨🚨\n\n💥 {offer_type.upper()} OFFER DELETED")

        await callback.message.edit_text("✅ Deletion completed")
    except Exception as e:
        logger.error(f"Delete operation failed: {e}")

    await callback.answer("Deleted")


# =============================
#  Offer editing handlers
# =============================
@dp.callback_query(F.data.startswith("edit_"))
async def edit_offer(callback: types.CallbackQuery, state: FSMContext):
    """Starts offer quantity editing process."""
    action, offer_id, quantity = callback.data.split(":")
    offer_type = action.split("_")[1]

    await state.update_data(
        offer_id=offer_id,
        offer_type=offer_type,
        quantity=quantity,
        message_id=callback.message.message_id,
        message_text=callback.message.text,
        message_reply_markup=callback.message.reply_markup
    )
    await callback.message.reply(f"Enter new quantity for {offer_type.upper()} offer.\nCurrent: {quantity}\n\n/cancel to abort")
    await state.set_state(EditOffer.waiting_for_new_value)
    await callback.answer()
    logger.info(f"Editing {offer_type.upper()} offer (id={offer_id}) initiated")


@dp.message(EditOffer.waiting_for_new_value)
async def receive_new_value(message: types.Message, state: FSMContext):
    """Receives new quantity from user."""
    if message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Action cancelled.")
        return

    if not message.text.isdigit() or message.text.startswith('-'):
        await message.answer("❌ Please enter a valid positive number.")
        return

    new_value = int(message.text)
    data = await state.get_data()
    offer_id, offer_type, quantity = data["offer_id"], data["offer_type"], data["quantity"]

    if new_value == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Confirm delete", callback_data=f"confirm_delete:{offer_type}:{offer_id}:{data['message_id']}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]])
        await message.answer(f"⚠️ Quantity = 0 means deletion. Confirm?", reply_markup=kb)
        return

    await state.update_data(new_value=new_value)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_edit"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    ]])
    await message.answer(f"Change quantity from {quantity} → {new_value}?", reply_markup=kb)
    await state.set_state(EditOffer.waiting_for_confirmation)


@dp.callback_query(F.data == "confirm_edit")
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    """Applies quantity update to DB and updates message text."""
    data = await state.get_data()
    offer_id = int(data["offer_id"])
    offer_type = data["offer_type"]
    new_value = int(data["new_value"])
    msg_id = data["message_id"]
    text = data["message_text"]
    markup = data["message_reply_markup"]

    await state.clear()

    try:
        await update_quantity_in_offer_by_id(offer_id, new_value)
        logger.info(f"Updated {offer_type.upper()} offer (id={offer_id}) to quantity={new_value}")
    except Exception as e:
        logger.error(f"Failed to update offer quantity: {e}")

    # Update message text
    lines = text.splitlines()
    section_start = "📤 SELL OFFER" if offer_type.upper() == 'SELL' else "📥 BUY OFFER"
    in_section = False

    for i, line in enumerate(lines):
        if line.strip().startswith(section_start):
            in_section = True
            continue
        if in_section and line.strip().startswith("📦 Quantity:"):
            prefix = "📦 Quantity: "
            pos = line.find(prefix) + len(prefix)
            lines[i] = line[:pos] + str(new_value)
            break

    updated_text = "\n".join(lines)

    try:
        await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=msg_id, text=updated_text, reply_markup=markup)
    except Exception as e:
        logger.warning(f"Could not update message text: {e}")

    await callback.message.reply(f"✅ {offer_type.upper()} offer updated.")
    await callback.answer("Updated")


# =============================
#  Cancel handlers
# =============================
@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    """Cancels any ongoing FSM action."""
    await state.clear()
    await callback.message.edit_text("❌ Action cancelled.")
    await callback.answer("Cancelled")


@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    """Cancels from /cancel command."""
    await state.clear()
    await message.answer("❌ Action cancelled.")


# =============================
#  Bot execution
# =============================
async def bot_execution():
    logger.info("Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(bot_execution())
