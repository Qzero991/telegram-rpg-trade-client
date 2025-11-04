import asyncio
import textwrap
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import settings


bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

# ===========================================
#  FSM: состояния для редактирования оффера
# ===========================================
class EditOffer(StatesGroup):
    waiting_for_new_value = State()
    waiting_for_confirmation = State()


# ===========================================
#  Уведомление об арбитраже
# ===========================================
async def send_telegram_message(query_result):
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
        ]
    ])

    await bot.send_message(settings.my_id, text, reply_markup=keyboard)


# ===========================================
#  Обработка удаления
# ===========================================
@dp.callback_query(F.data.startswith("delete_"))
async def delete_offer(callback: types.CallbackQuery):
    action, offer_id= callback.data.split(":")
    offer_type = action.split("_")[1]  # "buy" или "sell"

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_delete:{offer_type}:{offer_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]
    ])
    await callback.message.reply(
        f"Are you sure you want to delete the {offer_type.upper()} offer?",
        reply_markup=confirm_kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_delete"))
async def confirm_delete(callback: types.CallbackQuery):
    _, offer_type, offer_id = callback.data.split(":")
    # TODO: удалить из базы
    # delete_offer_from_db(offer_type, offer_id)
    await callback.message.edit_text(f"✅ {offer_type.upper()} offer was deleted successfully.")
    await callback.answer("Deleted")


# ===========================================
#  Обработка редактирования
# ===========================================
@dp.callback_query(F.data.startswith("edit_"))
async def edit_offer(callback: types.CallbackQuery, state: FSMContext):
    action, offer_id, quantity = callback.data.split(":")
    offer_type = action.split("_")[1]  # "buy" или "sell"

    await state.update_data(offer_id=offer_id, offer_type=offer_type, quantity=quantity)
    await callback.message.answer(
        f"Enter new quantity for {offer_type.upper()} offer.\nCurrent quantity is {quantity if quantity!="None" else "undefined"}\n\n/cancel to abort"
    )
    await state.set_state(EditOffer.waiting_for_new_value)
    await callback.answer()


@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Action cancelled.")

@dp.message(EditOffer.waiting_for_new_value)
async def receive_new_value(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or message.text[0] == '-':
        await message.answer("❌ Please enter a valid number.")
        return

    data = await state.get_data()
    quantity = data["quantity"]

    new_value = int(message.text)

    await state.update_data(new_value=new_value)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_edit"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]
    ])
    await message.answer(f"Change quantity from {quantity} to {new_value}?", reply_markup=kb)
    await state.set_state(EditOffer.waiting_for_confirmation)


@dp.callback_query(F.data == "confirm_edit")
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    quantity = data["quantity"]
    offer_id = data["offer_id"]
    offer_type = data["offer_type"]
    new_value = data["new_value"]

    # TODO: обновить в базе
    # update_offer_quantity(offer_type, offer_id, new_value)

    await callback.message.edit_text(
        f"✅ {offer_type.upper()} offer quantity updated from {quantity} to {new_value}."
    )
    await state.clear()
    await callback.answer("Updated")


@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Action cancelled.")
    await callback.answer("Cancelled")





# ===========================================
#  Запуск long polling
# ===========================================
async def main():
    print("Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())




