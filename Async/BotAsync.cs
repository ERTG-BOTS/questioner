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
      var thisMessage = update.Message
                  ?? update.CallbackQuery?.Message;
      if (thisMessage == null || thisMessage.Type == MessageType.MessagePinned) { return; }
      UserModel? currentUser;
      if (update.Message != null || update.CallbackQuery != null)
      {
        long chatId = thisMessage.Chat.Id;
        currentUser = await GetCorrectUserAsync(chatId, thisMessage.Chat.Username ?? "Скрыто/не определено");

        if (currentUser == null) { return; }

        string thisMessageText = update.Type == UpdateType.Message
            ? thisMessage.Caption
              ?? thisMessage.Text
              ?? thisMessage.WebAppData?.ButtonText
              ?? thisMessage.Document?.FileName
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
            await botClient.SendTextMessageAsync(chatId,
                "Линия доступна по ссылке http://46.146.231.248/linenck\nЛогин : <code>admin</code>\nПароль : <code>RO0admin</code>",
                parseMode: ParseMode.Html);
            return;
          case "/reset":
            currentUser.CurrentMode = currentUser.DefaultMode;
            await botClient.SendTextMessageAsync(chatId,
                "Статус сброшен",
                replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
            return;
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
                await botClient.SendTextMessageAsync(chatId,
                    "Отправь вопрос и вложения одним сообщением",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                await SendDefault(currentUser);
                return;
            }
          case 3:
            switch (currentMessage)
            {
              case "отменить вопрос":
                currentUser.CurrentMode = ModeCode["signed"];
                await botClient.SendTextMessageAsync(chatId,
                    "Чтобы задать вопрос нажми \"Задать вопрос\"",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
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
                  await botClient.SendTextMessageAsync(chatId,
                      "Вопрос был добавлен в очередь",
                      replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                }
                else
                {
                  await botClient.SendTextMessageAsync(chatId,
                      "Вопрос не был добавлен в очередь\n\nПопробуй еще раз",
                      replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                }
                return;
            }
          case 4:
            switch (currentMessage)
            {
              case "отменить вопрос":
                currentUser.CurrentMode = ModeCode["signed"];
                await QueueManager.RemoveFromQuestionQueueAsync(chatId);
                await botClient.SendTextMessageAsync(chatId,
                    "Чтобы задать вопрос нажми \"Задать вопрос\"",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                await botClient.SendTextMessageAsync(chatId,
                    "Вопрос уже в очереди",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
            }
          #endregion
          #region Старший
          case 20:
            switch (currentMessage)
            {
              case "стать спецом":
                currentUser.CurrentMode = ModeCode["signed"];
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты специалист",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              case "стать старшим":
                currentUser.CurrentMode = ModeCode["signed rg"];
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты специалист",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                await SendDefault(currentUser);
                return;
            }
          case 10:
            switch (currentMessage)
            {
              case "готов":
                currentUser.CurrentMode = ModeCode["ready rg"];
                await QueueManager.AddToReadyQueueAsync(
                      new ReadyChatRecord()
                      {
                        ChatId = chatId,
                        FIO = currentUser.FIO,
                        TimeStart = DateTime.UtcNow
                      });
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты готов",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                await SendDefault(currentUser);
                return;
            }
          case 11:
            switch (currentMessage)
            {
              case "не готов":
                currentUser.CurrentMode = ModeCode["signed rg"];
                await QueueManager.RemoveFromReadyQueueAsync(chatId);
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты не готов",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                await SendDefault(currentUser);
                return;
            }
          case 13:
            switch (currentMessage)
            {
              case "готов":
                await QueueManager.RemoveFromAwaitQueueAsync(chatId);
                currentUser.CurrentMode = ModeCode["ready rg"];
                await QueueManager.AddToReadyQueueAsync(new ReadyChatRecord() { ChatId = chatId, FIO = currentUser.FIO, TimeStart = DateTime.UtcNow });
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты готов",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              case "не готов":
                await QueueManager.RemoveFromAwaitQueueAsync(chatId);
                currentUser.CurrentMode = ModeCode["signed rg"];
                await QueueManager.RemoveFromReadyQueueAsync(chatId);
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты не готов",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
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
                currentUser.CurrentMode = ModeCode["signed"];
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты специалист",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              case "стать старшим":
                currentUser.CurrentMode = ModeCode["signed rg"];
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь ты специалист",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              case "файл с диалогами":
                await DocumentAsync.DialogHistoryExcel(currentUser.ChatId, DateTime.Now.Month);
                return;
              case "debug":
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
                await botClient.SendTextMessageAsync(chatId,
                    "Теперь в диалоге",
                    replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
                return;
              default:
                var dialogHistory = db.DialogHistoryModels.FirstOrDefault(x => x.TokenDialog == message.Text);
                if (dialogHistory != null)
                {
                  await DocumentAsync.DialogHistoryPDF(currentUser.ChatId, dialogHistory);
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
        await botClient.SendTextMessageAsync(chatId,
            "Произошла непредвиденная ошибка. Вы были возвращены к началу.",
            replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
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
      if (callbackQuery.Data == null || callbackQuery.Message == null || callbackQuery.Message.Text == null)
      {
        WriteLog("Error", $" Ошибка CallbackQuery. ChatId : {chatId} , Data : {callbackQuery.Data ?? "NULL"} , MessageText : {callbackQuery.Message?.Text ?? "NULL"}");
        if (callbackQuery.Message != null)
          await botClient.EditMessageTextAsync(chatId,
              callbackQuery.Message.MessageId,
              "Произошла ошибка",
              replyMarkup: null);
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
            await botClient.EditMessageTextAsync(chatId,
                callbackQuery.Message!.MessageId,
                "Оценка диалога проставлена",
                replyMarkup: null);
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
      await botClient.EditMessageTextAsync(chatId,
          callbackQuery.Message.MessageId,
          "Произошла ошибка",
          replyMarkup: null);
      return;
    }
    catch (Exception ex)
    {
      WriteLog("Error", $"Ошибка в HandleCallBackQuery: {ex.Message}\n{ex.StackTrace}");
      try
      {
        await botClient.EditMessageReplyMarkupAsync(chatId,
          callbackQuery.Message!.MessageId,
          replyMarkup: null);
      }
      finally
      {
        try { await botClient.SendTextMessageAsync(chatId, "Произошла ошибка попробуй другую кнопку"); }
        catch { }
      }
      return;
    }
  }

  public static async Task SendDefault(UserModel currentUser)
  {
    await botClient.SendTextMessageAsync(currentUser.ChatId,
        "Не распознал твоё сообщение 😓\nВоспользуйся всплывающей клавиатурой",
        replyMarkup: GetCurrentKeyboard(currentUser.CurrentMode));
  }
}
