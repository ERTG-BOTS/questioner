from aiogram.fsm.context import FSMContext
from aiogram.types import Message


async def disable_previous_buttons(message: Message, state: FSMContext):
    """Функция для отключения inline кнопок в сообщениях"""
    state_data = await state.get_data()
    messages_with_buttons = state_data.get("messages_with_buttons", [])

    for msg_id in messages_with_buttons:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id, message_id=msg_id, reply_markup=None
            )
        except Exception as e:
            # Handle case where message might be deleted or not editable
            print(f"Could not disable buttons for message {msg_id}: {e}")

    # Clear the list after disabling buttons
    await state.update_data(messages_with_buttons=[])