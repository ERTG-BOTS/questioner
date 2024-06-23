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

        bool isTopic = chatId == Config.TopicId;
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
    if (message.MessageThreadId == null || message.MessageThreadId == 3 || chatId == Config.BotChatId) return;

    var currentUser = UsersList.First(x => x.ChatId == chatId);
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
              ChatId = Config.TopicId,
              MessageThreadId = message.MessageThreadId,
              Text = "Диалога в данном чате не найдено\nЧат будет закрыт"
            }
          );
          try
          {
            await botClient.EditForumTopicAsync(
              new EditForumTopicRequest()
              {
                ChatId = Config.TopicId,
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
                ChatId = Config.TopicId,
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
          ChatId = Config.TopicId,
          MessageThreadId = message.MessageThreadId,
          Text = "Диалога в данном чате не найдено\nЧат будет закрыт"
        });
      await botClient.CloseForumTopicAsync(
        new CloseForumTopicRequest()
        {
          ChatId = Config.TopicId,
          MessageThreadId = (int)message.MessageThreadId
        });
      await botClient.EditForumTopicAsync(
        new EditForumTopicRequest()
        {
          ChatId = Config.TopicId,
          MessageThreadId = (int)message.MessageThreadId,
          IconCustomEmojiId = "5372819184658949787"
        });
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = Config.TopicId,
          MessageThreadId = 3,
          Text = $"Не найден диалог в чате {Config.TopicUrl}/{message.MessageThreadId}"
        });
      return;
    }
    if (message.Type == MessageType.Text)
    {
      switch (currentMessage.Split('@')[0])
      {
        case "/start":
          if (dialog.ChatIdLastSupervisor != 0)
          {
            await botClient.SendMessageAsync(
              new SendMessageRequest()
              {
                ChatId = Config.TopicId,
                MessageThreadId = message.MessageThreadId,
                Text = "Нельзя взять этот чат в работу",
                ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
              });
          }
          else
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
                  ChatId = Config.TopicId,
                  MessageThreadId = message.MessageThreadId,
                  Text = $"Чат в работу был взят {currentUser.FIO}",
                  ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
                });
              await botClient.EditForumTopicAsync(
                new EditForumTopicRequest()
                {
                  ChatId = Config.TopicId,
                  MessageThreadId = (int)message.MessageThreadId,
                  IconCustomEmojiId = "5368808634392257474"
                });
            }
            finally
            {
              QueueManager.dialogSemaphore.Release();
            }
          }
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
                  ChatId = Config.TopicId,
                  MessageThreadId = message.MessageThreadId,
                  Text = $"Чат был освобожден {currentUser.FIO}",
                  ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
                });
              await botClient.EditForumTopicAsync(
                new EditForumTopicRequest()
                {
                  ChatId = Config.TopicId,
                  MessageThreadId = (int)message.MessageThreadId,
                  IconCustomEmojiId = "5417915203100613993"
                }
              );
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
                ChatId = Config.TopicId,
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
                ChatId = Config.TopicId,
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
                ChatId = Config.TopicId,
                MessageThreadId = message.MessageThreadId,
                Text = $"Это не твой чат",
                ReplyParameters = new ReplyParameters() { MessageId = message.MessageId }
              });
          }
          return;
        default: break;
      }
    }
    if (dialog.ChatIdLastSupervisor == chatId)
      await QueueManager.DeliveryMessageDialogAsync(dialog, message.MessageId);
    else
    {
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = Config.TopicId,
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
        currentUser = await GetCorrectUserAsync(message.Chat.Id == Config.TopicId, chatId) ?? throw new Exception($"Не удалось получить пользователя {chatId}");

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
                var dialogList = db.DialogHistory
                                  .Where(x => x.FIOEmployee == currentUser.FIO)
                                  .OrderBy(x => x.FirstMessageId)
                                  .ToList()
                                  .Where(x =>
                                    DateTime.TryParse(x.StartQuestion, out var dateTime)
                                    && dateTime > DateTime.UtcNow.AddDays(-1))
                                  .TakeLast(3);

                if (dialogList.Count() != 0)
                {
                  List<string> sendDialog = [];
                  int counter = 1;
                  foreach (var dialog in dialogList)
                  {
                    var firstMessage = await botClient.EditMessageReplyMarkupAsync(
                      new EditMessageReplyMarkupRequest()
                      {
                        ChatId = Config.TopicId,
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
                        ChatId = Config.TopicId,
                        MessageId = dialog.FirstMessageId,
                        ReplyMarkup = null
                      });

                    sendDialog.Add(@$"{counter++}. {dialog.StartQuestion}
{firstMessage.Text ?? "Текста нет"}");
                  }

                  await botClient.SendMessageAsync(
                    new SendMessageRequest()
                    {
                      ChatId = chatId,
                      Text = string.Join("\n\n", sendDialog),
                      ReplyMarkup = new InlineKeyboardMarkup(KeyboardButtonsEmployees(dialogList.Count()))
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
                  var sendMessage =
                    sendMessageRequest("Теперь ты специалист", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
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
                      Text = $"{Config.TopicUrl}/{dialogHistory.FirstMessageId}"
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
                                    DateTime.TryParse(x.StartQuestion, out var dateTime)
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
