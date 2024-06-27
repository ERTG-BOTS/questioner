using System.Text;
using Telegram.Bot;
using Telegram.Bot.Exceptions;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;
using QuestionBot.Data;
using QuestionBot.Data.Models;
using static QuestionBot.Data.Substitution;
using static QuestionBot.Data.Models.UserModel;
using static QuestionBot.Program;
using static QuestionBot.Data.Keyboards;
using QuestionBot.Data.QueueModels;
using Telegram.Bot.Requests;
using Telegram.Bot.Types.ReplyMarkups;
using System.Data.Common;
using System.Security.Cryptography;
using System.Globalization;

namespace QuestionBot.Async;

internal class BotAsync
{
  private static List<string> FindedUser = [];

#pragma warning disable IDE0060 // Удалите неиспользуемый параметр
  /// <summary>
  /// Хук ошибок от API Телеграмм
  /// </summary>
  public static Task HandleErrorAsync(ITelegramBotClient botClient, Exception exception, CancellationToken cancellationToken)
  {
    string errorMsg = exception switch
    {
      ApiRequestException apiRequestException => $"[API | \x1b[41mERROR\x1b[0m] {DateTime.UtcNow:d MMM yyyy | HH:mm:ss} Error Telegram API: Error code: {apiRequestException.ErrorCode}; Exception message: {apiRequestException.Message}",
      _ => exception.ToString()
    };
    WriteLog("Error", errorMsg);
    Environment.Exit(999);
    return Task.CompletedTask;
  }

  /// <summary>
  /// Хук Update для бота
  /// </summary>
  public static async Task HandleUpdateAsync(ITelegramBotClient botClient, Update update, CancellationToken cancellationToken)
#pragma warning restore IDE0060 // Удалите неиспользуемый параметр
  {
    try
    {
      var thisMessage = update.Message ??
                  (Message?)update.CallbackQuery?.Message;
      if (thisMessage == null) { return; }
      UserModel? currentUser;
      if (update.Message != null || update.CallbackQuery != null)
      {
        long chatId = thisMessage?.Chat.Id ?? 0;

        bool isTopic = chatId == Config.ForumId;
        if (isTopic)
          chatId = thisMessage?.From?.Id ?? 0;

        if (chatId == Config.BotChatId) return;

        currentUser = await GetCorrectUserAsync(isTopic, chatId, thisMessage?.Chat.Username ?? "Скрыто/не определено");

        if (currentUser == null) { return; }

        string thisMessageText = update.Type == UpdateType.Message
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
      else return;
    }
    catch (Exception ex)
    {
      WriteLog("Error", $"Error in HandleUpdate. {ex.Message}\n{ex.StackTrace}");
    }
  }

  static async Task HandleTopicAsync(Message message, long chatId)
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
        {
          await botClient.PromoteChatMemberAsync(
            new PromoteChatMemberRequest()
            {
              ChatId = Config.ForumId,
              UserId = chatId,
              CanManageChat = true,
              CanDeleteMessages = true,
              CanManageVideoChat = true,
              CanRestrictMembers = true,
              CanPromoteMembers = true,
              CanChangeInfo = true,
              CanInviteUsers = true,
              CanPostMessages = true,
              CanPinMessages = true,
              CanManageTopics = true
            });
        }
      }
      catch { }
      return;
    }

    #region Старший
    string currentMessage = message.Text?.ToLower().Split('@')[0] ?? "";
    var dialog = QueueManager.DialogChats.FirstOrDefault(x => x.MessageThreadId == message.MessageThreadId);
    if (dialog == null)
    {
      using var db = new AppDbContext();
      {
        var checkDialog = db.DialogHistory.FirstOrDefault(x => x.MessageThreadId == message.MessageThreadId);

        if (checkDialog != null)
        {
          await botClient.SendMessageAsync(
            new SendMessageRequest()
            {
              ChatId = Config.ForumId,
              MessageThreadId = message.MessageThreadId,
              Text = "Диалога в данном чате не найдено\nЧат будет закрыт"
            }
          );
          try
          {
            await botClient.EditForumTopicAsync(
              new EditForumTopicRequest()
              {
                ChatId = Config.ForumId,
                MessageThreadId = (int)message.MessageThreadId,
                IconCustomEmojiId = "5312315739842026755",
                Name = checkDialog.Token
              }
            );
          }
          catch { }
          try
          {
            await botClient.CloseForumTopicAsync(
              new CloseForumTopicRequest()
              {
                ChatId = Config.ForumId,
                MessageThreadId = (int)message.MessageThreadId
              }
            );
          }
          catch { }
          return;
        }
      }
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = Config.ForumId,
          MessageThreadId = message.MessageThreadId,
          Text = "Диалога в данном чате не найдено\nЧат будет закрыт"
        });
      await botClient.CloseForumTopicAsync(
        new CloseForumTopicRequest()
        {
          ChatId = Config.ForumId,
          MessageThreadId = (int)message.MessageThreadId
        });
      await botClient.EditForumTopicAsync(
        new EditForumTopicRequest()
        {
          ChatId = Config.ForumId,
          MessageThreadId = (int)message.MessageThreadId,
          IconCustomEmojiId = EmojiKeys["lost"]
        });
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = Config.ForumId,
          MessageThreadId = 3,
          Text = $"Не найден диалог в чате {Config.TopicUrl}/{message.MessageThreadId}"
        });
      return;
    }
    if (message.Type == MessageType.Text)
    {
      switch (currentMessage.Split('@')[0])
      {
        case "/help":
          await botClient.SendMessageAsync(
            new SendMessageRequest()
            {
              ChatId = Config.ForumId,
              MessageThreadId = message.MessageThreadId,
              Text =
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
              ParseMode = ParseMode.Html,
              ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
            });
          return;
        case "/release":
          if (dialog.ChatIdLastSupervisor == currentUser.ChatId)
          {
            await QueueManager.dialogSemaphore.WaitAsync();
            try
            {
              dialog.ChatIdLastSupervisor = 0;
              dialog.ListEndDialog.Add(GetCorrectDateTime);
              await botClient.SendMessageAsync(
                new SendMessageRequest()
                {
                  ChatId = Config.ForumId,
                  MessageThreadId = message.MessageThreadId,
                  Text = $"Чат был освобожден {currentUser.FIO}",
                  ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
                });
              await botClient.EditForumTopicAsync(
                new EditForumTopicRequest()
                {
                  ChatId = Config.ForumId,
                  MessageThreadId = (int)message.MessageThreadId,
                  IconCustomEmojiId = EmojiKeys["new"]
                });
              await botClient.SendMessageAsync(
                new SendMessageRequest()
                {
                  ChatId = dialog.ChatIdEmployee,
                  Text = $"Старший вышел из чата, твой вопрос сейчас на рассмотрении"
                });
            }
            finally
            {
              QueueManager.dialogSemaphore.Release();
            }
          }
          else
          {
            await botClient.SendMessageAsync(
              new SendMessageRequest()
              {
                ChatId = Config.ForumId,
                MessageThreadId = message.MessageThreadId,
                Text = $"Это не твой чат",
                ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
              });
          }
          return;
        case "/end":
          if (dialog.ChatIdLastSupervisor == currentUser.ChatId)
          {
            await QueueManager.EndDialogAsync(dialog);
            await botClient.SendMessageAsync(
              new SendMessageRequest()
              {
                ChatId = Config.ForumId,
                MessageThreadId = message.MessageThreadId,
                Text = $"Чат был закрыт {currentUser.FIO}",
                ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
              });
          }
          else
          {
            await botClient.SendMessageAsync(
              new SendMessageRequest()
              {
                ChatId = Config.ForumId,
                MessageThreadId = message.MessageThreadId,
                Text = $"Это не твой чат",
                ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
              });
          }
          return;
        default: break;
      }
    }
    if (dialog.ChatIdLastSupervisor == 0)
    {
      await QueueManager.dialogSemaphore.WaitAsync();
      try
      {
        dialog.ChatIdLastSupervisor = chatId;
        dialog.ListFIOSupervisor.Add(currentUser.FIO);
        dialog.ListStartDialog.Add(GetCorrectDateTime);
        await botClient.SendMessageAsync(
          new SendMessageRequest()
          {
            ChatId = Config.ForumId,
            MessageThreadId = message.MessageThreadId,
            Text = $"Чат в работу был взят {currentUser.FIO}",
            ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
          });
        await botClient.EditForumTopicAsync(
          new EditForumTopicRequest()
          {
            ChatId = Config.ForumId,
            MessageThreadId = (int)message.MessageThreadId,
            IconCustomEmojiId = EmojiKeys["start"]
          });
        await botClient.SendMessageAsync(
          new SendMessageRequest()
          {
            ChatId = dialog.ChatIdEmployee,
            Text = $"На твой вопрос отвечает {currentUser.FIO}"
          });
      }
      finally
      {
        QueueManager.dialogSemaphore.Release();
      }
    }
    if (dialog.ChatIdLastSupervisor == chatId)
      await QueueManager.DeliveryMessageDialogAsync(dialog, message.MessageId);
    else
    {
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = Config.ForumId,
          MessageThreadId = message.MessageThreadId,
          Text = $"Это не твой чат",
          ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
        });
    }
    #endregion
  }

  /// <summary>
  /// Обработка отправленного сообщения от пользователя
  /// </summary>
  /// <param name="message">Объект Message из Update</param>
  /// <param name="chatId">ChatId пользователя</param>
  static async Task HandleMessageAsync(Message message, long chatId)
  {
    if (message.Type == MessageType.Text
    || message.Type == MessageType.Document
    || message.Type == MessageType.Photo
    || message.Type == MessageType.Video
    || message.Type == MessageType.Sticker)
    {
      SendMessageRequest sendMessageRequest(string text, int mode) => new()
      {
        ChatId = chatId,
        Text = text,
        ReplyMarkup = GetCurrentKeyboard(mode),
        ParseMode = ParseMode.Html
      };

      UserModel currentUser = UsersList.First(x => x.ChatId == chatId);
      StringBuilder output = new();
      using AppDbContext db = new();
      var resultDb = db.RegisteredUsers.FirstOrDefault(x => x.ChatId == chatId);
      if (resultDb == null && currentUser.DefaultMode != ModeCode["default"])
        currentUser = await GetCorrectUserAsync(message.Chat.Id == Config.ForumId, chatId) ?? throw new Exception($"Не удалось получить пользователя {chatId}");

      string currentMessage = message.Text?.ToLower() ?? message.Caption?.ToLower() ?? "";

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
                await botClient.SendMessageAsync(
                  new SendMessageRequest()
                  {
                    ChatId = chatId,
                    Text =
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
                  }
                );
                return;
              case "задать вопрос":
                currentUser.CurrentMode = ModeCode["question"];
                SendMessageRequest sendMessage = new()
                {
                  ChatId = chatId,
                  Text = "Отправь вопрос и вложения одним сообщением",
                  ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
                };
                await botClient.SendMessageAsync(sendMessage);
                return;
              case "вернуть вопрос":
                await botClient.SendMessageAsync(
                  new SendMessageRequest()
                  {
                    ChatId = chatId,
                    Text = "Загружаю список вопросов",
                  });
                var dialogList = db.DialogHistory
                                  .Where(x => x.FIOEmployee == currentUser.FIO)
                                  .OrderBy(x => x.FirstMessageId)
                                  .ToList()
                                  .Where(x =>
                                    DateTime.TryParseExact(x.StartQuestion, "dd.MM.yyyy HH:mm:ss", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateTime)
                                      && dateTime > DateTime.UtcNow.AddDays(-1))
                                  .TakeLast(3);

                if (dialogList.Count() != 0)
                {
                  List<string> sendDialog = [];
                  int counter = 1;
                  foreach (var dialog in dialogList)
                  {
                    try
                    {
                      var firstMessage = await botClient.EditMessageReplyMarkupAsync(
                      new EditMessageReplyMarkupRequest()
                      {
                        ChatId = Config.ForumId,
                        MessageId = dialog.FirstMessageId,
                        ReplyMarkup = new InlineKeyboardMarkup(
                          new[]
                          {
                              new InlineKeyboardButton[]
                              {
                                  InlineKeyboardButton.WithCallbackData("1", "callback_data_1")
                              }
                          })
                      });

                      await botClient.EditMessageReplyMarkupAsync(
                        new EditMessageReplyMarkupRequest()
                        {
                          ChatId = Config.ForumId,
                          MessageId = dialog.FirstMessageId,
                          ReplyMarkup = null
                        });

                      sendDialog.Add(@$"{counter++}. {dialog.StartQuestion}
{firstMessage.Text ?? firstMessage.Caption ?? "Текста нет"}");
                    }
                    catch (Exception ex)
                    {
                      WriteLog("Error", ex.Message);
                    }
                  }

                  await botClient.SendMessageAsync(
                    new SendMessageRequest()
                    {
                      ChatId = chatId,
                      Text = string.Join("\n\n", sendDialog),
                      ReplyMarkup = new InlineKeyboardMarkup(KeyboardButtonsEmployees(dialogList.Count()))
                    });
                }
                else
                {
                  await botClient.SendMessageAsync(
                    new SendMessageRequest()
                    {
                      ChatId = chatId,
                      Text = "Список вопросов пуст, вернуть нечего"
                    });
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
                  var sendMessage = sendMessageRequest("Чтобы задать вопрос нажми \"Задать вопрос\"", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                {
                  if (await QueueManager.AddToQuestionQueueAsync(
                      new QuestionChatRecord()
                      {
                        ChatId = chatId,
                        FIO = currentUser.FIO,
                        StartMessageId = message.MessageId,
                        TimeStart = DateTime.UtcNow
                      }))
                  {
                    currentUser.CurrentMode = ModeCode["await answer"];
                    var sendMessage = sendMessageRequest("Вопрос был добавлен в очередь", currentUser.CurrentMode);
                    await botClient.SendMessageAsync(sendMessage);
                  }
                  else
                  {
                    var sendMessage = sendMessageRequest("Вопрос не был добавлен в очередь\n\nПопробуй еще раз", currentUser.CurrentMode);
                    await botClient.SendMessageAsync(sendMessage);
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
                  var sendMessage = sendMessageRequest("Чтобы задать вопрос нажми \"Задать вопрос\"", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                {
                  var sendMessage = sendMessageRequest("Вопрос уже в очереди", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
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
                  var a = await botClient.GetForumTopicIconStickersAsync(new GetForumTopicIconStickersRequest());
                  List<string> strings = [];
                  foreach (var item in a)
                  {
                    strings.Add($"{item.Emoji} | {item.CustomEmojiId}");
                  }
                  currentUser.CurrentMode = ModeCode["signed"];
                  await botClient.SendMessageAsync(
                    new SendMessageRequest()
                    {
                      ChatId = chatId,
                      Text = $"Теперь ты специалист",
                      ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
                    });
                  return;
                }
              case "максмум диалогов":
                await botClient.SendMessageAsync(
                  new SendMessageRequest()
                  {
                    ChatId = chatId,
                    Text = $"Текущее максимальное количество диалогов {Config.DialogMaxCount}\nЧтобы изменить максмальное количество диалогов, отправь число\n0 - снять ограничение",
                    ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
                  });
                return;
              case "файл с диалогами":
                await botClient.SendMessageAsync(
                  new SendMessageRequest()
                  {
                    ChatId = chatId,
                    Text = "За какой месяц отправить?",
                    ReplyMarkup = new InlineKeyboardMarkup(
                          new[]
                          {
                              new InlineKeyboardButton[]
                              {
                                  InlineKeyboardButton.WithCallbackData(russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.Month), "0")
                              },
                              [
                                  InlineKeyboardButton.WithCallbackData(russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.Month - 1), "1")
                              ],
                              [
                                  InlineKeyboardButton.WithCallbackData(russianCulture.DateTimeFormat.GetMonthName(DateTime.Now.Month - 2), "2")
                              ]
                          })
                  }
                );
                return;
              default:
                var dialogHistory = db.DialogHistory.FirstOrDefault(x => x.Token == message.Text);
                if (dialogHistory != null)
                {
                  await botClient.SendMessageAsync(
                    new SendMessageRequest()
                    {
                      ChatId = chatId,
                      Text = $"{Config.TopicUrl}/{dialogHistory.FirstMessageId}",
                      ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
                    }
                  );
                }
                else
                {
                  var oldDiaglogHistory = db.OldDialogHistory.FirstOrDefault(x => x.TokenDialog == message.Text);
                  if (oldDiaglogHistory is not null)
                  {
                    _ = Task.Run(() => DocumentAsync.DialogHistoryPDF(chatId, oldDiaglogHistory));
                  }
                  else
                  {
                    if (int.TryParse(message.Text, out var count) && count >= 0)
                    {
                      Config.DialogMaxCount = count;
                      await botClient.SendMessageAsync(
                        new SendMessageRequest()
                        {
                          ChatId = chatId,
                          Text = $"Максимальное количество диалогов установлено на {count}",
                          ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
                        });
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
        var sendMessage =
                  sendMessageRequest("Произошла непредвиденная ошибка. Вы были возвращены к началу.", currentUser.CurrentMode);
        await botClient.SendMessageAsync(sendMessage);
        return;
      }
    }

    return;
  }

  /// <summary>
  /// Обработка CallBack запросов
  /// </summary>
  /// <param name="callbackQuery">Объект CallbackQuery из Update</param>
  /// <param name="chatId">ChatId пользователя</param>
  static async Task HandleCallBackQuery(CallbackQuery callbackQuery, long chatId)
  {
    try
    {
      var message = (Message?)callbackQuery.Message;
      if (callbackQuery.Data == null || callbackQuery.Message == null || message?.Text == null)
      {
        WriteLog("Error", $" Ошибка CallbackQuery. ChatId : {chatId} , Data : {callbackQuery.Data ?? "NULL"} , MessageText : {message?.Text ?? "NULL"}");
        if (callbackQuery.Message != null)
        {
          await botClient.EditMessageTextAsync(
                new EditMessageTextRequest
                {
                  ChatId = chatId,
                  MessageId = message!.MessageId,
                  Text = "Произошла ошибка",
                  ReplyMarkup = null
                });
        }
        return;
      }
      string[] currentData = callbackQuery.Data.Split('#');
      StringBuilder output = new();
      var currentUser = UsersList.First(x => x.ChatId == chatId);

      using (var db = new AppDbContext())

        switch (currentUser.CurrentMode)
        {
          #region Сотрудник
          case 2 or 20:
            if (currentData.Length == 2)
            {
              var dialog = db.DialogHistory.FirstOrDefault(x => x.Token == currentData[1]);
              if (dialog != null)
              {
                dialog.DialogQuality = currentData[0] == "good";
              }
              db.SaveChanges();
              await botClient.EditMessageTextAsync(
                    new EditMessageTextRequest
                    {
                      ChatId = chatId,
                      MessageId = message!.MessageId,
                      Text = "Оценка диалога проставлена",
                      ReplyMarkup = null
                    });
            }
            else if (currentData.Length == 1)
            {
              var dialogList = db.DialogHistory
                                  .Where(x => x.FIOEmployee == currentUser.FIO)
                                  .OrderBy(x => x.FirstMessageId)
                                  .ToList()
                                  .Where(x =>
                                    DateTime.TryParseExact(x.StartQuestion, "dd.MM.yyyy HH:mm:ss", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateTime)
                                    && dateTime > DateTime.UtcNow.AddDays(-1))
                                  .TakeLast(3)
                                  .ToList();

              if (int.TryParse(currentData[0], out var num) && dialogList.Count >= num)
              {
                await botClient.EditMessageReplyMarkupAsync(
                  new EditMessageReplyMarkupRequest
                  {
                    ChatId = chatId,
                    MessageId = message!.MessageId,
                    ReplyMarkup = null
                  });
                await QueueManager.AddDialogAsync(dialogList[num - 1], chatId);
              }
            }
            return;
          case 3 or 4 or 5: return;
          #endregion
          #region Администратор
          case 100:
            await botClient.EditMessageReplyMarkupAsync(new EditMessageReplyMarkupRequest()
            {
              ChatId = chatId,
              MessageId = message!.MessageId,
              ReplyMarkup = null
            });
            if (currentData.Length == 1)
            {
              await DocumentAsync.DialogHistoryExcel(currentUser.ChatId, DateTime.Now.Month - int.Parse(currentData[0]));
              await DocumentAsync.OldDialogHistoryExcel(currentUser.ChatId, DateTime.Now.Month - int.Parse(currentData[0]));
            }

            return;
          #endregion
          default: break;
        }
      WriteLog("Error", $"CurrentMode : {currentUser.CurrentMode} CurrentData {string.Join(", ", currentData.Select((s, i) => $"[{i}] = {s}"))}");
      await botClient.EditMessageTextAsync(
            new EditMessageTextRequest
            {
              ChatId = chatId,
              MessageId = message!.MessageId,
              Text = "Произошла ошибка",
              ReplyMarkup = null
            });
      return;
    }
    catch (Exception ex)
    {
      WriteLog("Error", $"Ошибка в HandleCallBackQuery: {ex.Message}\n{ex.StackTrace}");
      try
      {
        await botClient.EditMessageReplyMarkupAsync(
              new EditMessageReplyMarkupRequest()
              {
                ChatId = chatId,
                MessageId = ((Message?)callbackQuery.Message)!.MessageId,
                ReplyMarkup = null
              });
      }
      finally
      {
        try
        {
          await botClient.SendMessageAsync(
                new SendMessageRequest()
                {
                  ChatId = chatId,
                  Text = "Произошла ошибка. Попробуй другую кнопку",
                });
        }
        catch { }
      }
      return;
    }
  }

  public static async Task SendDefault(UserModel currentUser)
  {
    await botClient.SendMessageAsync(
          new SendMessageRequest()
          {
            ChatId = currentUser.ChatId,
            Text = "Не распознал твоё сообщение 😓\nВоспользуйся всплывающей клавиатурой",
            ReplyMarkup = GetCurrentKeyboard(currentUser.CurrentMode)
          });
  }
}
