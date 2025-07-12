using System.Globalization;
using System.Text;
using QuestionBot.Data;
using QuestionBot.Data.Models;
using QuestionBot.Data.QueueModels;
using Telegram.Bot;
using Telegram.Bot.Exceptions;
using Telegram.Bot.Requests;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;
using Telegram.Bot.Types.ReplyMarkups;
using static QuestionBot.Data.Substitution;
using static QuestionBot.Data.Models.UserModel;
using static QuestionBot.Program;
using static QuestionBot.Data.Keyboards;

namespace QuestionBot.Async;

internal class BotAsync
{
    private static List<string> FindedUser = [];

    private static async Task HandleTopicAsync(Message message, long chatId)
    {
        var currentUser = UsersList.First(x => x.ChatId == chatId);
        if (message.MessageThreadId == null
            || message.MessageThreadId == 3
            || chatId == Config.BotChatId
            || message.MessageThreadId == 1)
        {
            try
            {
                if (currentUser.DefaultMode == ModeCode["signed root"])
                    await botClient.PromoteChatMember(
                        Config.ForumId,
                        chatId,
                        canManageChat: true,
                        canDeleteMessages: true,
                        canManageVideoChats: true,
                        canRestrictMembers: true,
                        canPromoteMembers: true,
                        canChangeInfo: true,
                        canInviteUsers: true,
                        canPostMessages: true,
                        canPinMessages: true,
                        canManageTopics: true
                    );
            }
            catch
            {
            }

            return;
        }

        #region Старший

        var currentMessage = message.Text?.ToLower().Split('@')[0] ?? "";
        var dialog = QueueManager.DialogChats.FirstOrDefault(x => x.MessageThreadId == message.MessageThreadId);
        if (dialog == null)
        {
            using var db = new AppDbContext();
            {
                var checkDialog = db.DialogHistory.FirstOrDefault(x => x.MessageThreadId == message.MessageThreadId);

                if (checkDialog != null)
                {
                    await botClient.SendMessage(
                        Config.ForumId,
                        messageThreadId: message.MessageThreadId,
                        text: "Диалога в данном чате не найдено\nЧат будет закрыт"
                    );
                    try
                    {
                        await botClient.EditForumTopic(
                            Config.ForumId,
                            (int)message.MessageThreadId,
                            iconCustomEmojiId: "5312315739842026755",
                            name: checkDialog.Token
                        );
                    }
                    catch
                    {
                    }

                    try
                    {
                        await botClient.CloseForumTopic(
                            Config.ForumId,
                            (int)message.MessageThreadId
                        );
                    }
                    catch
                    {
                    }

                    return;
                }
            }
            await botClient.SendMessage(
                Config.ForumId,
                messageThreadId: message.MessageThreadId,
                text: "Диалога в данном чате не найдено\nЧат будет закрыт"
            );
            await botClient.CloseForumTopic(
                Config.ForumId,
                (int)message.MessageThreadId
            );
            await botClient.EditForumTopic(
                Config.ForumId,
                (int)message.MessageThreadId,
                iconCustomEmojiId: EmojiKeys["lost"]
            );
            await botClient.SendMessage(
                Config.ForumId,
                messageThreadId: 3,
                text: $"Не найден диалог в чате {Config.TopicUrl}/{message.MessageThreadId}"
            );
            return;
        }

        if (message.Type == MessageType.Text)
            switch (currentMessage.Split('@')[0])
            {
                case "/help":
                    await botClient.SendMessage(
                        Config.ForumId,
                        messageThreadId: message.MessageThreadId,
                        text:
                        @"Инструкция для работы с диалогами для старших

Создание тем для диалогов:
- Если ограничение на количество диалогов в группе не достигнуто, создается тема, название которой соответствует ФИО Специалиста.
- На теме появляется значок 💬.

Забрать диалог:
- Каждый диалог с значком 💬 может быть забран одним из Старших с помощью команды 
- Диалог будет взят в работу после первого сообщения, если ранее его никто не взял
- В диалоге может быть только один старший. Сообщения других старших не дойдут до специалиста, и бот ответит ""Это не твой чат"".

Диалог в работе:
- После того, как диалог забрали, значок меняется на 💅.
- Сообщения Старшего, который забрал диалог, будут пересылаться специалисту в бота.

Завершение или освобождение диалога:
- Диалог может завершить Специалист или Старший, который забрал этот диалог.
- Диалог может освободить Старший, который забрал этот диалог.
- Завершить или освободить чат до того, как его забрали, нельзя.

Команды для управления диалогом:
- Чтобы завершить диалог, нужно написать 
<copy>/end</copy>
 После этого бот напишет ""Диалог завершен"", закроет тему, название поменяется на уникальный токен, а значок на 🏆.
- Чтобы освободить диалог, нужно написать 
<copy>/release</copy>
В этом случае значок меняется на 💬, и чат может забрать любой Старший.",
                        parseMode: ParseMode.Html,
                        replyParameters: new ReplyParameters { MessageId = message.MessageId }
                    );
                    return;
                case "/release":
                    if (dialog.ChatIdLastSupervisor == currentUser.ChatId)
                    {
                        await QueueManager.dialogSemaphore.WaitAsync();
                        try
                        {
                            dialog.ChatIdLastSupervisor = 0;
                            dialog.ListEndDialog.Add(GetCorrectDateTime);
                            await botClient.SendMessage(
                                Config.ForumId,
                                messageThreadId: message.MessageThreadId,
                                text: $"Чат был освобожден {currentUser.FIO}",
                                replyParameters: new ReplyParameters { MessageId = message.MessageId }
                            );
                            await botClient.EditForumTopic(
                                Config.ForumId,
                                (int)message.MessageThreadId,
                                iconCustomEmojiId: EmojiKeys["new"]
                            );
                            await botClient.SendMessage(
                                dialog.ChatIdEmployee,
                                "Старший вышел из чата, твой вопрос сейчас на рассмотрении"
                            );
                        }
                        finally
                        {
                            QueueManager.dialogSemaphore.Release();
                        }
                    }
                    else
                    {
                        await botClient.SendMessage(
                            Config.ForumId,
                            messageThreadId: message.MessageThreadId,
                            text: "Это не твой чат",
                            replyParameters: new ReplyParameters { MessageId = message.MessageId }
                        );
                    }

                    return;
                case "/end":
                    if (dialog.ChatIdLastSupervisor == currentUser.ChatId)
                    {
                        await QueueManager.EndDialogAsync(dialog);
                        await botClient.SendMessage(
                            Config.ForumId,
                            messageThreadId: message.MessageThreadId,
                            text: $"Чат был закрыт {currentUser.FIO}",
                            replyParameters: new ReplyParameters { MessageId = message.MessageId }
                        );
                        await botClient.SendMessage(
                            Config.ForumId,
                            messageThreadId: message.MessageThreadId,
                            text: "Мог ли специалист решить вопрос самостоятельно?",
                            replyParameters: new ReplyParameters { MessageId = message.MessageId },
                            replyMarkup: DialogQualityRg(dialog.Token)
                        );
                    }
                    else
                    {
                        await botClient.SendMessage(
                            Config.ForumId,
                            messageThreadId: message.MessageThreadId,
                            text: "Это не твой чат",
                            replyParameters: new ReplyParameters { MessageId = message.MessageId }
                        );
                    }

                    return;
            }

        if (dialog.ChatIdLastSupervisor == 0)
        {
            await QueueManager.dialogSemaphore.WaitAsync();
            try
            {
                dialog.ChatIdLastSupervisor = chatId;
                dialog.ListFIOSupervisor.Add(currentUser.FIO);
                dialog.ListStartDialog.Add(GetCorrectDateTime);
                await botClient.SendMessage(
                    Config.ForumId,
                    messageThreadId: message.MessageThreadId,
                    text: $"Чат в работу был взят <b>{currentUser.FIO}</b>",
                    replyParameters: new ReplyParameters { MessageId = message.MessageId },
                    parseMode: ParseMode.Html
                );
                await botClient.EditForumTopic(
                    Config.ForumId,
                    (int)message.MessageThreadId,
                    iconCustomEmojiId: EmojiKeys["start"]
                );
                await botClient.SendMessage(
                    dialog.ChatIdEmployee,
                    $"На твой вопрос отвечает {currentUser.FIO}"
                );
            }
            finally
            {
                QueueManager.dialogSemaphore.Release();
            }
        }

        if (dialog.ChatIdLastSupervisor == chatId)
            await QueueManager.DeliveryMessageDialogAsync(dialog, message.MessageId);
        else
            await botClient.SendMessage(
                Config.ForumId,
                messageThreadId: message.MessageThreadId,
                text: "Это не твой чат",
                replyParameters: new ReplyParameters { MessageId = message.MessageId }
            );

        #endregion
    }

    /// <summary>
    ///     Обработка отправленного сообщения от пользователя
    /// </summary>
    /// <param name="message">Объект Message из Update</param>
    /// <param name="chatId">ChatId пользователя</param>
    private static async Task HandleMessageAsync(Message message, long chatId)
    {
        if (message.Type == MessageType.Text
            || message.Type == MessageType.Document
            || message.Type == MessageType.Photo
            || message.Type == MessageType.Video
            || message.Type == MessageType.Sticker)
        {
            SendMessageRequest sendMessageRequest(string text, int mode)
            {
                return new SendMessageRequest
                {
                    ChatId = chatId,
                    Text = text,
                    ReplyMarkup = GetCurrentKeyboard(mode),
                    ParseMode = ParseMode.Html
                };
            }

            var currentUser = UsersList.First(x => x.ChatId == chatId);
            StringBuilder output = new();
            using AppDbContext db = new();
            var resultDb = db.RegisteredUsers.FirstOrDefault(x => x.ChatId == chatId);
            if (resultDb == null && currentUser.DefaultMode != ModeCode["default"])
                currentUser = await GetCorrectUserAsync(message.Chat.Id == Config.ForumId, chatId) ??
                              throw new Exception($"Не удалось получить пользователя {chatId}");

            var currentMessage = message.Text?.ToLower() ?? message.Caption?.ToLower() ?? "";

            if (currentUser.FIO == null) return;

            try
            {
                switch (currentUser.CurrentMode)
                {
                    #region Сотрудник

                    case 2 or 20:
                        switch (currentMessage)
                        {
                            case "/release":
                                currentUser.CurrentMode = currentUser.DefaultMode;
                                return;
                            case "/help":
                                await botClient.SendMessage(
                                    chatId,
                                    @"Задаем вопрос:
- Нажмите кнопку ""Задать вопрос"".
- Напишите одно сообщение с текстом вопроса.
- Постарайтесь сформулировать вопрос максимально понятно, чтобы тебе было проще его идентифицировать.

Очередь вопросов:
- Как только вопрос задан, он попадает в очередь. Бот сообщит: ""Вопрос был добавлен в очередь"".
- Если есть свободные слоты, чат передается Старший. Бот сообщит: ""Вопрос передан на рассмотрение"".

Обмен сообщениями с Старшим:
- После передачи вопроса на рассмотрение можно отправлять любое количество сообщений, которые Старший получит.
- Когда свободный Старший возьмет твой диалог в работу, ты получишь сообщение: ""На твой вопрос отвечает XXXXXXX"".

Передача вопроса между специалистами:
- Старший может передать ваш вопрос другому старшему, если это потребуется. Бот сообщит: ""Старший вышел из чата, твой вопрос сейчас на рассмотрении"".
- Впоследствии вопрос заберет другой Старший.

Закрытие вопроса:
- Вопрос может закрыть как старший специалист, так и Старший.

Возврат чатов специалистом:
- Специалист может вернуть один из трех последних чатов.
- Идентифицировать вопрос можно по первому сообщению или времени, когда был задан вопрос.
- История общения по этому вопросу будет у Старшего."
                                );
                                return;
                            case "задать вопрос":
                                currentUser.CurrentMode = ModeCode["question"];
                                await botClient.SendMessage(
                                    chatId,
                                    "Отправь вопрос и вложения одним сообщением",
                                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
                                );
                                return;
                            case "вернуть вопрос":
                                await botClient.SendMessage(
                                    chatId,
                                    "Загружаю список вопросов"
                                );
                                var dialogList = db.DialogHistory
                                    .Where(x => x.FIOEmployee == currentUser.FIO)
                                    .OrderBy(x => x.FirstMessageId)
                                    .ToList()
                                    .Where(x =>
                                        DateTime.TryParseExact(x.StartQuestion, "dd.MM.yyyy HH:mm:ss",
                                            CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateTime)
                                        && dateTime > DateTime.UtcNow.AddDays(-1))
                                    .TakeLast(3);

                                if (dialogList.Count() != 0)
                                {
                                    List<string> sendDialog = [];
                                    var counter = 1;
                                    foreach (var dialog in dialogList)
                                        try
                                        {
                                            var firstMessage = await botClient.EditMessageReplyMarkup(
                                                Config.ForumId,
                                                dialog.FirstMessageId,
                                                new InlineKeyboardMarkup(
                                                    new[]
                                                    {
                                                        new[]
                                                        {
                                                            InlineKeyboardButton.WithCallbackData("1",
                                                                "callback_data_1")
                                                        }
                                                    })
                                            );

                                            await botClient.EditMessageReplyMarkup(
                                                Config.ForumId,
                                                dialog.FirstMessageId
                                            );

                                            sendDialog.Add(@$"{counter++}. {dialog.StartQuestion}
{firstMessage.Text ?? firstMessage.Caption ?? "Текста нет"}");
                                        }
                                        catch (Exception ex)
                                        {
                                            WriteLog("Error", ex.Message);
                                        }

                                    await botClient.SendMessage(
                                        chatId,
                                        string.Join("\n\n", sendDialog),
                                        replyMarkup: new InlineKeyboardMarkup(
                                            KeyboardButtonsEmployees(dialogList.Count()))
                                    );
                                }
                                else
                                {
                                    await botClient.SendMessage(
                                        chatId,
                                        "Список вопросов пуст, вернуть нечего"
                                    );
                                }

                                return;
                            default:
                                await SendDefault(currentUser);
                                return;
                        }
                    case 3:
                        switch (currentMessage)
                        {
                            case "отменить вопрос":
                            {
                                currentUser.CurrentMode = ModeCode["signed"];
                                await botClient.SendMessage(
                                    text: "Чтобы задать вопрос нажми \"Задать вопрос\"",
                                    chatId: currentUser.CurrentMode
                                );
                                return;
                            }
                            default:
                            {
                                await botClient.SendMessage(chatId: currentUser.ChatId,
                                    text: "Прикрепи ссылку на регламент из клевера, по которому у тебя вопрос");
                                currentUser.CurrentMode = ModeCode["clever"];
                                break;
                            }
                        }

                        break;
                    case 33:
                        switch (currentMessage)
                        {
                            case "отменить вопрос":
                            {
                                currentUser.CurrentMode = ModeCode["signed"];
                                // var sendMessage = sendMessageRequest("Чтобы задать вопрос нажми \"Задать вопрос\"", currentUser.CurrentMode);
                                await botClient.SendMessage(
                                    text: "Чтобы задать вопрос нажми \"Задать вопрос\"",
                                    chatId: currentUser.CurrentMode
                                );
                                return;
                            }
                            default:
                            {
                                if (!message.Text.Contains("clever.ertelecom.ru/content/space/") && currentUser.Role != 10)
                                {
                                    await botClient.SendMessage(chatId: message.Chat.Id,
                                        text:
                                        "<b>Сообщение не содержит ссылку на клевер</b>\nОтправь ссылку на регламент из клевера, по которому у тебя вопрос", parseMode: ParseMode.Html);
                                    return;
                                }
                                
                                if (await QueueManager.AddToQuestionQueueAsync(
                                        new QuestionChatRecord
                                        {
                                            ChatId = chatId,
                                            FIO = currentUser.FIO,
                                            StartMessageId = message.MessageId,
                                            TimeStart = DateTime.UtcNow,
                                            CleverLink = currentUser.CurrentMode == 10 ? "Заглушка" : message.Text
                                        }))
                                {
                                    currentUser.CurrentMode = ModeCode["await answer"];
                                    // var sendMessage = sendMessageRequest("Вопрос был добавлен в очередь", currentUser.CurrentMode);
                                    await botClient.SendMessage(
                                        text: "Вопрос был добавлен в очередь",
                                        chatId: currentUser.CurrentMode
                                    );
                                }
                                else
                                {
                                    // var sendMessage = sendMessageRequest("Вопрос не был добавлен в очередь\n\nПопробуй еще раз", currentUser.CurrentMode);
                                    await botClient.SendMessage(
                                        text: "Вопрос не был добавлен в очередь\\n\\nПопробуй еще раз",
                                        chatId: currentUser.CurrentMode
                                    );
                                }

                                return;
                            }
                        }
                    case 4:
                        switch (currentMessage)
                        {
                            case "отменить вопрос":
                            {
                                currentUser.CurrentMode = ModeCode["signed"];
                                await QueueManager.RemoveFromQuestionQueueAsync(chatId);
                                // var sendMessage = sendMessageRequest("Чтобы задать вопрос нажми \"Задать вопрос\"", currentUser.CurrentMode);
                                await botClient.SendMessage(
                                    text: "Чтобы задать вопрос нажми \"Задать вопрос\"",
                                    chatId: currentUser.CurrentMode
                                );
                                return;
                            }
                            default:
                            {
                                // var sendMessage = sendMessageRequest("Вопрос уже в очереди", currentUser.CurrentMode);
                                await botClient.SendMessage(
                                    text: "Вопрос уже в очереди",
                                    chatId: currentUser.CurrentMode
                                );
                                return;
                            }
                        }
                    case 5:
                        switch (currentMessage)
                        {
                            case "завершить диалог":
                                await QueueManager.EndDialogAsync(chatId);
                                return;
                            default:
                                await QueueManager.DeliveryMessageDialogAsync(chatId, message.MessageId);
                                return;
                        }

                    #endregion

                    #region Администратор

                    case 100:
                        switch (currentMessage)
                        {
                            case "стать спецом":
                            {
                                // var a = await botClient.GetForumTopicIconStickers(new GetForumTopicIconStickersRequest());
                                var a = await botClient.GetForumTopicIconStickers();
                                List<string> strings = [];
                                foreach (var item in a) strings.Add($"{item.Emoji} | {item.CustomEmojiId}");
                                currentUser.CurrentMode = ModeCode["signed"];
                                await botClient.SendMessage(
                                    chatId,
                                    "Теперь ты специалист",
                                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
                                );
                                return;
                            }
                            case "максимум диалогов":
                                await botClient.SendMessage(
                                    chatId,
                                    $"Текущее максимальное количество диалогов {Config.DialogMaxCount}\nЧтобы изменить максмальное количество диалогов, отправь число\n0 - снять ограничение",
                                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
                                );
                                return;
                            case "файл с диалогами":
                                await botClient.SendMessage(
                                    chatId,
                                    "За какой месяц отправить?",
                                    replyMarkup: ReportMonthSelector()
                                );
                                return;
                            default:
                                var dialogHistory = db.DialogHistory.FirstOrDefault(x => x.Token == message.Text);
                                if (dialogHistory != null)
                                {
                                    await botClient.SendMessage(
                                        chatId,
                                        $"{Config.TopicUrl}/{dialogHistory.FirstMessageId}",
                                        replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
                                    );
                                }
                                else
                                {
                                    var oldDiaglogHistory =
                                        db.OldDialogHistory.FirstOrDefault(x => x.TokenDialog == message.Text);
                                    if (oldDiaglogHistory is not null)
                                    {
                                        _ = Task.Run(() => DocumentAsync.DialogHistoryPDF(chatId, oldDiaglogHistory));
                                    }
                                    else
                                    {
                                        if (int.TryParse(message.Text, out var count) && count >= 0)
                                        {
                                            Config.DialogMaxCount = count;
                                            await botClient.SendMessage(
                                                chatId,
                                                $"Максимальное количество диалогов установлено на {count}",
                                                replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
                                            );
                                            return;
                                        }

                                        await SendDefault(currentUser);
                                    }
                                }

                                return;
                        }

                    #endregion

                    default: throw new Exception($"Неизвестный currentMode {currentUser.CurrentMode}");
                }
            }
            catch (Exception ex)
            {
                WriteLog("Error", $"{ex.Message}\n{ex.StackTrace}");
                // var sendMessage = sendMessageRequest("Произошла непредвиденная ошибка. Вы были возвращены к началу.", currentUser.CurrentMode);
                await botClient.SendMessage(
                    text: "Произошла непредвиденная ошибка. Вы были возвращены к началу.",
                    chatId: currentUser.CurrentMode
                );
            }
        }
    }

    /// <summary>
    ///     Обработка CallBack запросов
    /// </summary>
    /// <param name="callbackQuery">Объект CallbackQuery из Update</param>
    /// <param name="chatId">ChatId пользователя</param>
    private static async Task HandleCallBackQuery(CallbackQuery callbackQuery, long chatId)
    {
        try
        {
            WriteLog("callback", $"{chatId} {callbackQuery.Data}");
            var message = callbackQuery.Message;
            if (callbackQuery.Data == null || callbackQuery.Message == null || message?.Text == null)
            {
                WriteLog("Error",
                    $" Ошибка CallbackQuery. ChatId : {chatId} , Data : {callbackQuery.Data ?? "NULL"} , MessageText : {message?.Text ?? "NULL"}");
                if (callbackQuery.Message != null)
                    await botClient.EditMessageText(
                        chatId,
                        message!.MessageId,
                        "Произошла ошибка",
                        replyMarkup: null
                    );
                return;
            }

            var currentData = callbackQuery.Data.Split('#');
            StringBuilder output = new();
            using var db = new AppDbContext();
            
            if (currentData.Length == 3 && currentData[0] == "rg" && chatId == Config.BotChatId)
            {
                var dialog = db.DialogHistory.FirstOrDefault(x => x.Token == currentData[2]);
                
                var topicSupervisor = GetUser(callbackQuery.From.Id);
                var topicSupervisorsList = db.DialogHistory.FirstOrDefault(x => x.Token == currentData[2])?.ListFIOSupervisor;

                if (topicSupervisor != null && topicSupervisorsList != null && topicSupervisorsList.Contains(topicSupervisor.FIO))
                {
                    if (dialog != null) dialog.DialogQualityRg = currentData[1] == "good";
                    await db.SaveChangesAsync();
                    await botClient.EditMessageText(
                        Config.ForumId,
                        message!.MessageId,
                        "Оценка диалога проставлена",
                        replyMarkup: null
                    );
                }
                else
                {
                    await botClient.AnswerCallbackQuery(callbackQuery.Id, "Это не твой чат");
                }

                return;
            }

            var currentUser = UsersList.First(x => x.ChatId == chatId);

            switch (currentUser.CurrentMode)
            {
                #region Сотрудник

                case 2 or 20:
                    if (currentData.Length == 2)
                    {
                        var dialog = db.DialogHistory.FirstOrDefault(x => x.Token == currentData[1]);
                        if (dialog != null) dialog.DialogQuality = currentData[0] == "good";
                        db.SaveChanges();
                        await botClient.EditMessageText(
                            chatId,
                            message!.MessageId,
                            "Оценка диалога проставлена",
                            replyMarkup: null
                        );
                    }

                    else if (currentData.Length == 1)
                    {
                        var dialogList = db.DialogHistory
                            .Where(x => x.FIOEmployee == currentUser.FIO)
                            .OrderBy(x => x.FirstMessageId)
                            .ToList()
                            .Where(x =>
                                DateTime.TryParseExact(x.StartQuestion, "dd.MM.yyyy HH:mm:ss",
                                    CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateTime)
                                && dateTime > DateTime.UtcNow.AddDays(-1))
                            .TakeLast(3)
                            .ToList();

                        if (int.TryParse(currentData[0], out var num) && dialogList.Count >= num)
                        {
                            await botClient.EditMessageReplyMarkup(
                                chatId,
                                message!.MessageId
                            );
                            await QueueManager.AddDialogAsync(dialogList[num - 1], chatId);
                        }
                    }

                    return;
                case 3 or 4 or 5: return;

                #endregion

                #region Администратор

                case 100:
                    await botClient.EditMessageReplyMarkup(
                        chatId,
                        message!.MessageId
                    );
                    if (currentData.Length == 1)
                    {
                        if (currentData[0] == "3")
                        {
                            await DocumentAsync.DialogHistoryExcel(currentUser.ChatId);
                            return;
                        }

                        await DocumentAsync.DialogHistoryExcel(currentUser.ChatId,
                            DateTime.Now.AddMonths(-int.Parse(currentData[0])).Month);
                        // await DocumentAsync.OldDialogHistoryExcel(currentUser.ChatId, DateTime.Now.AddMonths( - int.Parse(currentData[0])).Month);
                    }

                    return;

                #endregion

                default: break;
            }

            WriteLog("Error",
                $"CurrentMode : {currentUser.CurrentMode} CurrentData {string.Join(", ", currentData.Select((s, i) => $"[{i}] = {s}"))}");
            await botClient.EditMessageText(
                chatId,
                message!.MessageId,
                "Произошла ошибка",
                replyMarkup: null
            );
        }
        catch (Exception ex)
        {
            WriteLog("Error", $"Ошибка в HandleCallBackQuery: {ex.Message}\n{ex.StackTrace}");
            try
            {
                await botClient.EditMessageReplyMarkup(
                    chatId,
                    ((Message?)callbackQuery.Message)!.MessageId
                );
            }
            finally
            {
                try
                {
                    await botClient.SendMessage(
                        chatId,
                        "Произошла ошибка. Попробуй другую кнопку"
                    );
                }
                catch
                {
                }
            }
        }
    }

    public static async Task SendDefault(UserModel currentUser)
    {
        await botClient.SendMessage(
            currentUser.ChatId,
            "Не распознал твоё сообщение 😓\nВоспользуйся всплывающей клавиатурой",
            replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode)
        );
    }

    public static async Task DeleteOldTopics(DialogHistories[] topicList)
    {
        foreach (var topic in topicList)
        {
            try
            {
                await botClient.DeleteForumTopic(chatId: Config.ForumId, messageThreadId: topic.MessageThreadId);
                WriteLog("Топики", $"Удален топик {topic.MessageThreadId} ({topic.Token})");
            }catch (Exception ex)
            {
                WriteLog("Топики", $"Не удалось удалить топик {topic.MessageThreadId} ({topic.Token}). Ошибка:  {ex.Message}");
            }
            
        }
    }

#pragma warning disable IDE0060 // Удалите неиспользуемый параметр
  /// <summary>
  ///     Хук ошибок от API Телеграмм
  /// </summary>
  public static Task HandleErrorAsync(ITelegramBotClient botClient, Exception exception,
        CancellationToken cancellationToken)
    {
        var errorMsg = exception switch
        {
            ApiRequestException apiRequestException =>
                $"[API | \x1b[41mERROR\x1b[0m] {DateTime.UtcNow:d MMM yyyy | HH:mm:ss} Error Telegram API: Error code: {apiRequestException.ErrorCode}; Exception message: {apiRequestException.Message}",
            _ => exception.ToString()
        };
        WriteLog("Error", errorMsg);
        Environment.Exit(999);
        return Task.CompletedTask;
    }

  /// <summary>
  ///     Хук Update для бота
  /// </summary>
  public static async Task HandleUpdateAsync(ITelegramBotClient botClient, Update update,
        CancellationToken cancellationToken)
#pragma warning restore IDE0060 // Удалите неиспользуемый параметр
    {
        try
        {
            var thisMessage = update.Message ??
                              update.CallbackQuery?.Message;
            if (thisMessage == null) return;
            UserModel? currentUser;
            if (update.Message != null || update.CallbackQuery != null)
            {
                var chatId = thisMessage?.Chat.Id ?? 0;

                var isTopic = chatId == Config.ForumId;
                if (isTopic)
                    chatId = thisMessage?.From?.Id ?? 0;

                if (chatId == Config.BotChatId && update.Type == UpdateType.CallbackQuery &&
                    update.CallbackQuery?.Data is not null)
                {
                    await HandleCallBackQuery(update.CallbackQuery, chatId);
                    return;
                }

                if (chatId == Config.BotChatId)
                    return;

                currentUser = await GetCorrectUserAsync(isTopic, chatId,
                    thisMessage?.Chat.Username ?? "Скрыто/не определено");

                if (currentUser == null) return;

                var thisMessageText = update.Type == UpdateType.Message
                    ? thisMessage!.Caption
                      ?? thisMessage!.Text
                      ?? thisMessage!.WebAppData?.ButtonText
                      ?? thisMessage!.Document?.FileName
                      ?? "Сообщение не содержит текста"
                    : update.CallbackQuery?.Data
                      ?? "Callback без Data";

                WriteLog("Сообщение", $"{currentUser.Username} {currentUser.ChatId} {thisMessageText}");
                if (isTopic && update.Type == UpdateType.Message && update.Message != null)
                    await HandleTopicAsync(update.Message, currentUser.ChatId);
                else if (update.Type == UpdateType.Message && update.Message != null)
                    await HandleMessageAsync(update.Message, currentUser.ChatId);
                else if (update.Type == UpdateType.CallbackQuery && update.CallbackQuery != null)
                    await HandleCallBackQuery(update.CallbackQuery, currentUser.ChatId);
            }
            else
            {
                return;
            }
        }
        catch (Exception ex)
        {
            WriteLog("Error", $"Error in HandleUpdate. {ex.Message}\n{ex.StackTrace}");
        }
    }
}