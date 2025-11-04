import asyncio
import textwrap
import re
from telegram.tg_client import client
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

    # 🟩 NEW — добавлена кнопка Delete BOTH
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
            InlineKeyboardButton(text="💣 Delete BOTH", callback_data=f"delete_both:{buy_offer.id}:{sell_offer.id}")  # 🟩 NEW
        ]
    ])

    sent_message = await bot.send_message(settings.my_id, text, reply_markup=keyboard)
    return sent_message.message_id  # 🟩 пригодится для обновлений


# ===========================================
#  Обработка удаления
# ===========================================
@dp.callback_query(F.data.startswith("delete_"))
async def delete_offer(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    action = parts[0]
    offer_type = action.split("_")[1]  # "buy", "sell" или "both"

    # 🟩 удаление обоих офферов
    if offer_type == "both":
        buy_id, sell_id = parts[1], parts[2]
        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_delete:both:{buy_id}:{sell_id}:{callback.message.message_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]])
        await callback.message.reply("Are you sure you want to delete BOTH offers?", reply_markup=confirm_kb)
        await callback.answer()
        return

    # 🟩 удаление одного оффера
    offer_id = parts[1]
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_delete:{offer_type}:{offer_id}:{callback.message.message_id}"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    ]])
    await callback.message.reply(
        f"Are you sure you want to delete the {offer_type.upper()} offer?",
        reply_markup=confirm_kb
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_delete"))
async def confirm_delete(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    offer_type = parts[1]

    if offer_type == "both":
        buy_id, sell_id = parts[2], parts[3]
        # 🟩 TODO: удалить оба из базы
        # delete_offer_from_db("buy", buy_id)
        # delete_offer_from_db("sell", sell_id)

        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=int(parts[4]),
                text="🚨🚨  ARBITRAGE DELETED!  🚨🚨\n\n💥  BOTH OFFERS DELETED",
            )
        except Exception as e:
            print("Update message failed:", e)


    else:
        offer_type, offer_id = parts[1], parts[2]
        # 🟩 TODO: удалить из базы
        # delete_offer_from_db(offer_type, offer_id)
        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=int(parts[3]),
                text=f"🚨🚨  ARBITRAGE DELETED!  🚨🚨\n\n💥  {offer_type.upper()} OFFER DELETED",
            )
        except Exception as e:
            print("Update message failed:", e)


    # 🟩 также заменяем оригинальное сообщение
    try:
        await callback.message.edit_text("✅ Deletion completed")
    except Exception:
        pass

    await callback.answer("Deleted")


# ===========================================
#  Обработка редактирования
# ===========================================
@dp.callback_query(F.data.startswith("edit_"))
async def edit_offer(callback: types.CallbackQuery, state: FSMContext):
    action, offer_id, quantity = callback.data.split(":")
    offer_type = action.split("_")[1]  # "buy" или "sell"

    await state.update_data(
        offer_id=offer_id,
        offer_type=offer_type,
        quantity=quantity,
        message_id=callback.message.message_id,
        message_text=callback.message.text,
        message_reply_markup=callback.message.reply_markup
                                    # 🟩 сохраним ID сообщения для будущего редактирования
    )
    await callback.message.reply(
        f"Enter new quantity for {offer_type.upper()} offer.\nCurrent quantity: {quantity}\n\n/cancel to abort"
    )
    await state.set_state(EditOffer.waiting_for_new_value)
    await callback.answer()


@dp.message(EditOffer.waiting_for_new_value)
async def receive_new_value(message: types.Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Action cancelled.")
        return

    if not message.text.isdigit() or message.text[0] == '-':
        await message.answer("❌ Please enter a valid number.")
        return

    new_value = int(message.text)
    data = await state.get_data()
    offer_id = data["offer_id"]
    offer_type = data["offer_type"]
    quantity = data["quantity"]

    # 🟩 если новое значение = 0 — предупреждение об удалении
    if new_value == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Confirm delete", callback_data=f"confirm_delete:{offer_type}:{offer_id}:{data["message_id"]}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]])
        await message.answer(f"⚠️ This will delete the {offer_type} offer and arbitrage. Confirm?", reply_markup=kb)
        # 🟩 можно удалить предупреждение позже

        return

    await state.update_data(new_value=new_value)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirm", callback_data="confirm_edit"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    ]])
    await message.answer(f"Change quantity from {quantity} to {new_value}?", reply_markup=kb)
    await state.set_state(EditOffer.waiting_for_confirmation)


@dp.callback_query(F.data == "confirm_edit")
async def confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offer_id = data["offer_id"]
    offer_type = data["offer_type"]
    new_value = data["new_value"]
    msg_id = data["message_id"]
    text = data["message_text"]
    message_reply_markup = data["message_reply_markup"]

    await state.clear()

    # 🟩 TODO: обновить количество в базе
    # update_offer_quantity(offer_type, offer_id, new_value)

    # 🟩 обновляем исходное сообщение с новым количеством

    if offer_type.upper() not in ['SELL', 'BUY']:
        raise ValueError("Неверный offer_type: должен быть 'SELL' или 'BUY'")

    lines = text.splitlines()  # Разбиваем текст на строки
    in_section = False  # Флаг, что мы в нужном блоке
    section_start = "📤 SELL OFFER" if offer_type.upper() == 'SELL' else "📥 BUY OFFER"

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Входим в нужный блок
        if stripped.startswith(section_start):
            in_section = True
            continue

        # Если мы в блоке и нашли строку с Quantity
        if in_section and stripped.startswith("📦 Quantity:"):
            # Находим позицию числа: после "📦 Quantity: " (с учётом пробелов)
            prefix = "📦 Quantity: "
            number_start = line.find(prefix) + len(prefix)
            # Заменяем всю строку на новую с new_value
            lines[i] = line[:number_start] + str(new_value)
            break  # Замена сделана, выходим

    # Собираем текст обратно
    replaced_text = '\n'.join(lines)

    # Если замена не произошла (блок не найден), возвращаем оригинал с предупреждением
    if replaced_text == text:
        print("Предупреждение: Раздел для замены не найден.")

    try:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            text=replaced_text,
            reply_markup=message_reply_markup
        )
    except Exception as e:
        print("Update message failed:", e)

    await callback.message.reply(f"✅ {offer_type.upper()} offer updated successfully.")
    await state.clear()
    await callback.answer("Updated")


# ===========================================
#  Cancel
# ===========================================
@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Action cancelled.")
    await callback.answer("Cancelled")


@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Action cancelled.")


# ===========================================
#  Запуск long polling
# ===========================================
async def main():
    print("Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
