using Telegram.Bot.Types.ReplyMarkups;

namespace QuestionBot.Data;

class Keyboards
{
  /// <summary>
  /// Клавиатура для пользователя на основе его текущего состояния
  /// </summary>
  /// <param name="modeCode">Состояние пользователя</param>
  /// <returns>готовую клавиатуру</returns>
  public static ReplyKeyboardMarkup GetCurrentKeyboard(int modeCode) => modeCode switch
  {
    2 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new("Задать вопрос")
        ]
      })
    { ResizeKeyboard = true },
    3 or 4 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Отменить вопрос")
        ]
      })
    { ResizeKeyboard = true },
    10 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Готов")
        ]
      })
    { ResizeKeyboard = true },
    11 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Не готов")
        ]
      })
    { ResizeKeyboard = true },
    5 or 12 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Завершить диалог")
        ]
      })
    { ResizeKeyboard = true },
    13 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Готов")
        ],
        [
          new ("Не готов")
        ],
      })
    { ResizeKeyboard = true },
    20 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Стать спецом"), new("Стать старшим")
        ]
      })
    { ResizeKeyboard = true },
    100 => new ReplyKeyboardMarkup(new KeyboardButton[][]
      {
        [
          new ("Стать спецом"), new("Стать старшим")
        ],
        [
          new("Файл с диалогами")
        ]
      })
    { ResizeKeyboard = true },
    _ => new ReplyKeyboardMarkup(new[] { new[] { new KeyboardButton("Авторизация") } }) { ResizeKeyboard = true },
  };

  /// <summary>
  /// Генерирует клавиатуру, в зависимости от количества найденных пользователей
  /// </summary>
  /// <param name="countEmployee">Количество пользователей</param>
  /// <returns></returns>
  public static InlineKeyboardButton[][] KeyboardButtonsEmployees(int countEmployee)
  {
    InlineKeyboardButton[][] keyboardInline = new InlineKeyboardButton[(countEmployee > 4) ? 2 : 1][];
    InlineKeyboardButton[] keyboardButtonsRow = new InlineKeyboardButton[(countEmployee > 4) ? countEmployee - 4 : countEmployee];
    InlineKeyboardButton[] keyboardButtonsRow1 = new InlineKeyboardButton[4];

    if (countEmployee < 5)
    {
      for (int i = 0; i < countEmployee; i++)
      {
        keyboardButtonsRow[i] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
      }
      keyboardInline[0] = keyboardButtonsRow;
    }
    else
    {
      for (int i = 0; i < 4; i++)
      {
        keyboardButtonsRow1[i] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
      }
      keyboardInline[0] = keyboardButtonsRow1;
      for (int i = 4; i < countEmployee; i++)
      {
        keyboardButtonsRow[i - 4] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
      }
      keyboardInline[1] = keyboardButtonsRow;
    }
    return keyboardInline;
  }

  public static InlineKeyboardMarkup DialogQuality(string token)
  {
    return new(new[]
    {
      new[]{ InlineKeyboardButton.WithCallbackData("Хорошо", $"good#{token}"), InlineKeyboardButton.WithCallbackData("Плохо", $"bad#{token}") },
    });
  }
}