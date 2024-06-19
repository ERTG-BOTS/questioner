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
        currentUser = await GetCorrectUserAsync(chatId, thisMessage?.Chat.Username ?? "Скрыто/не определено");

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
      }
      else return;
      if (update.Type == UpdateType.Message && update.Message != null)
        await HandleMessageAsync(update.Message, currentUser.ChatId);
      else if (update.Type == UpdateType.CallbackQuery && update.CallbackQuery != null)
        await HandleCallBackQuery(update.CallbackQuery, currentUser.ChatId);
    }
    catch (Exception ex)
    {
      WriteLog("Error", $"Error in HandleUpdate. {ex.Message}\n{ex.StackTrace}");
    }
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
        currentUser = await GetCorrectUserAsync(chatId) ?? throw new Exception($"Не удалось получить пользователя {chatId}");

      string currentMessage = message.Text?.ToLower() ?? message.Caption?.ToLower() ?? "";

      #region Общее
      if (currentUser.DefaultMode != ModeCode["default"])
      {
        switch (currentMessage)
        {
          case "/line":
            {
              var sendMessage =
                  sendMessageRequest("Линия доступна по ссылке http://46.146.231.248/linenck\nЛогин : <code>admin</code>\nПароль : <code>RO0admin</code>",
                  currentUser.CurrentMode);
              await botClient.SendMessageAsync(sendMessage);
              return;
            }
          case "/reset":
            {
              switch (currentUser.CurrentMode)
              {
                case 4:
                  if (QueueManager.QuestionQueue.Any(x => x.Value.ChatId == chatId))
                  {
                    await QueueManager.RemoveFromQuestionQueueAsync(chatId);
                  }
                  break;
                case 5 or 12:
                  if (QueueManager.DialogQueue.Any(x => x.Value.ChatIdSupervisor == chatId || x.Value.ChatIdEmployee == chatId))
                  {
                    await QueueManager.EndDialogAsync(chatId);
                  }
                  break;
                case 11:
                  if (QueueManager.ReadyQueue.Any(x => x.Value.ChatId == chatId))
                  {
                    await QueueManager.RemoveFromReadyQueueAsync(chatId);
                  }
                  break;
                case 13:
                  if (QueueManager.AwaitQueue.Any(x => x.Value.ChatId == chatId))
                  {
                    await QueueManager.RemoveFromAwaitQueueAsync(chatId);
                  }
                  break;
              }
              currentUser.CurrentMode = currentUser.DefaultMode;
              var sendMessage =
                  sendMessageRequest("Статус сброшен",
                  currentUser.CurrentMode);
              await botClient.SendMessageAsync(sendMessage);
              return;
            }
          default: break;
        }
      }
      #endregion

      if (currentUser.FIO == null) return;

      try
      {
        switch (currentUser.CurrentMode)
        {
          #region Сотрудник
          case 2:
            switch (currentMessage)
            {
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
          #endregion
          #region Старший
          case 20:
            switch (currentMessage)
            {
              case "стать спецом":
                {
                  currentUser.CurrentMode = ModeCode["signed"];
                  var sendMessage = sendMessageRequest("Теперь ты специалист", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              case "стать старшим":
                {
                  currentUser.CurrentMode = ModeCode["signed rg"];
                  var sendMessage = sendMessageRequest("Теперь ты старший", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                await SendDefault(currentUser);
                return;
            }
          case 10:
            switch (currentMessage)
            {
              case "готов":
                {
                  currentUser.CurrentMode = ModeCode["ready rg"];
                  await QueueManager.AddToReadyQueueAsync(
                        new ReadyChatRecord()
                        {
                          ChatId = chatId,
                          FIO = currentUser.FIO,
                          TimeStart = DateTime.UtcNow
                        });
                  var sendMessage = sendMessageRequest("Теперь ты готов", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                await SendDefault(currentUser);
                return;
            }
          case 11:
            switch (currentMessage)
            {
              case "не готов":
                {
                  currentUser.CurrentMode = ModeCode["signed rg"];
                  await QueueManager.RemoveFromReadyQueueAsync(chatId);
                  var sendMessage =
                        sendMessageRequest("Теперь ты не готов", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                await SendDefault(currentUser);
                return;
            }
          case 13:
            switch (currentMessage)
            {
              case "готов":
                {
                  await QueueManager.RemoveFromAwaitQueueAsync(chatId);
                  currentUser.CurrentMode = ModeCode["ready rg"];
                  await QueueManager.AddToReadyQueueAsync(new ReadyChatRecord() { ChatId = chatId, FIO = currentUser.FIO, TimeStart = DateTime.UtcNow });
                  var sendMessage =
                      sendMessageRequest("Теперь ты готов", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              case "не готов":
                {
                  await QueueManager.RemoveFromAwaitQueueAsync(chatId);
                  currentUser.CurrentMode = ModeCode["signed rg"];
                  await QueueManager.RemoveFromReadyQueueAsync(chatId);
                  var sendMessage =
                      sendMessageRequest("Теперь ты не готов", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                await SendDefault(currentUser);
                return;
            }
          #endregion
          #region Диалог
          case 5 or 12:
            switch (currentMessage)
            {
              case "завершить диалог":
                await QueueManager.EndDialogAsync(chatId);
                return;
              default:
                await QueueManager.AddToMessageHistoryAsync(chatId, message.MessageId);
                return;
            }
          #endregion
          #region Администратор
          case 100:
            switch (currentMessage)
            {
              case "стать спецом":
                {
                  currentUser.CurrentMode = ModeCode["signed"];
                  var sendMessage =
                    sendMessageRequest("Теперь ты специалист", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              case "стать старшим":
                {
                  currentUser.CurrentMode = ModeCode["signed rg"];
                  var sendMessage =
                    sendMessageRequest("Теперь ты старший", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                }
                return;
              case "файл с диалогами":
                await DocumentAsync.DialogHistoryExcel(currentUser.ChatId, DateTime.Now.Month);
                return;
              case "debug":
                {
                  await QueueManager.AddToDialogQueueAsync(new DialogChatRecord
                  {
                    ChatIdEmployee = chatId,
                    FIOEmployee = currentUser.FIO,
                    ChatIdSupervisor = chatId,
                    FIOSupervisor = currentUser.FIO,
                    TimeStart = DateTime.UtcNow,
                    TimeLast = DateTime.UtcNow,
                    MessageHistory = []
                  });
                  currentUser.CurrentMode = ModeCode["in dialog"];
                  var sendMessage =
                    sendMessageRequest("Теперь в диалоге", currentUser.CurrentMode);
                  await botClient.SendMessageAsync(sendMessage);
                  return;
                }
              default:
                var dialogHistory = db.DialogHistoryModels.FirstOrDefault(x => x.TokenDialog == message.Text);
                if (dialogHistory != null)
                {
                  _ = Task.Run(async () => await DocumentAsync.DialogHistoryPDF(currentUser.ChatId, dialogHistory));
                }
                else
                {
                  await SendDefault(currentUser);
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
          case 2:
            var dialog = db.DialogHistoryModels.FirstOrDefault(x => x.TokenDialog == currentData[1]);
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
            return;
          #endregion
          #region Старший
          case 10:
          #endregion
          #region Администратор
          case 100:
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
