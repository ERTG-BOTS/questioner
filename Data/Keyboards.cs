using Telegram.Bot.Types.ReplyMarkups;

namespace QuestionBot.Data;

internal class Keyboards
{
  /// <summary>
  ///     Клавиатура для пользователя на основе его текущего состояния
  /// </summary>
  /// <param name="modeCode">Состояние пользователя</param>
  /// <returns>готовую клавиатуру</returns>
  public static ReplyKeyboardMarkup GetCurrentKeyboard(int modeCode)
    {
        return modeCode switch
        {
            2 or 20 => new ReplyKeyboardMarkup(new KeyboardButton[][]
                {
                    [
                        new KeyboardButton("Задать вопрос")
                    ],
                    [
                        new KeyboardButton("Вернуть вопрос")
                    ]
                })
                { ResizeKeyboard = true },
            3 or 4 => new ReplyKeyboardMarkup(new KeyboardButton[][]
                {
                    [
                        new KeyboardButton("Отменить вопрос")
                    ]
                })
                { ResizeKeyboard = true },
            5 => new ReplyKeyboardMarkup(new KeyboardButton[][]
                {
                    [
                        new KeyboardButton("Завершить диалог")
                    ]
                })
                { ResizeKeyboard = true },
            100 => new ReplyKeyboardMarkup(new KeyboardButton[][]
                {
                    [
                        new KeyboardButton("Стать спецом")
                    ],
                    [
                        new KeyboardButton("Максимум диалогов")
                    ],
                    [
                        new KeyboardButton("Файл с диалогами")
                    ]
                })
                { ResizeKeyboard = true },
            _ => new ReplyKeyboardMarkup(new[] { new[] { new KeyboardButton("Авторизация") } })
                { ResizeKeyboard = true }
        };
    }

  /// <summary>
  ///     Генерирует клавиатуру, в зависимости от количества найденных пользователей
  /// </summary>
  /// <param name="countEmployee">Количество пользователей</param>
  /// <returns></returns>
  public static InlineKeyboardButton[][] KeyboardButtonsEmployees(int countEmployee)
    {
        var keyboardInline = new InlineKeyboardButton[countEmployee > 4 ? 2 : 1][];
        var keyboardButtonsRow = new InlineKeyboardButton[countEmployee > 4 ? countEmployee - 4 : countEmployee];
        var keyboardButtonsRow1 = new InlineKeyboardButton[4];

        if (countEmployee < 5)
        {
            for (var i = 0; i < countEmployee; i++)
                keyboardButtonsRow[i] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
            keyboardInline[0] = keyboardButtonsRow;
        }
        else
        {
            for (var i = 0; i < 4; i++)
                keyboardButtonsRow1[i] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
            keyboardInline[0] = keyboardButtonsRow1;
            for (var i = 4; i < countEmployee; i++)
                keyboardButtonsRow[i - 4] = InlineKeyboardButton.WithCallbackData((i + 1).ToString());
            keyboardInline[1] = keyboardButtonsRow;
        }

        return keyboardInline;
    }

    public static InlineKeyboardMarkup DialogQuality(string token)
    {
        return new InlineKeyboardMarkup(new[]
        {
            new[]
            {
                InlineKeyboardButton.WithCallbackData("Хорошо", $"good#{token}"),
                InlineKeyboardButton.WithCallbackData("Плохо", $"bad#{token}")
            }
        });
    }

    public static InlineKeyboardMarkup DialogQualityRg(string token)
    {
        return new InlineKeyboardMarkup(new[]
        {
            new[]
            {
                InlineKeyboardButton.WithCallbackData("Нет", $"rg#good#{token}"),
                InlineKeyboardButton.WithCallbackData("Да", $"rg#bad#{token}")
            }
        });
    }

    public static InlineKeyboardMarkup ReportMonthSelector()
    {
        return new[]
        {
            new[]
            {
                InlineKeyboardButton.WithCallbackData(
                    Program.russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.Month), "0")
            },
            [
                InlineKeyboardButton.WithCallbackData(
                    Program.russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.AddMonths(-1).Month), "1")
            ],
            [
                InlineKeyboardButton.WithCallbackData(
                    Program.russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.AddMonths(-2).Month), "2")
            ],
            [
                InlineKeyboardButton.WithCallbackData("3 месяца", "3")
            ]
        };
    }
}