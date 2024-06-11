using System.Globalization;
using Newtonsoft.Json;
using QuestionBot.Data;
using QuestionBot.Data.QueueModels;
using QuestionBot.Async;
using Telegram.Bot;
using Telegram.Bot.Polling;
using System.Security.Cryptography;

namespace QuestionBot;

public class Program
{
  public static ITelegramBotClient botClient = new TelegramBotClient("");
  public static List<Data.Models.UserModel> UsersList = [];
  public static ConfigInfo Config = new();
  public static QueueChatManager QueueManager = new();
  public static readonly CultureInfo russianCulture = new("ru-RU");
  static async Task Main()
  {
    botClient = new TelegramBotClient(Config.BotToken);
    Substitution.WriteLog("Start", $"Загрузка бота {botClient.GetMeAsync().Result.FirstName}...");

    CancellationTokenSource cts = new();
    CancellationToken cancellationToken = cts.Token;
    ReceiverOptions receiverOptions = new()
    {
      AllowedUpdates = { },
    };

    Config.PrintAllSettings();

    _ = Task.Run(async () =>
        {
          while (true)
          {
            await Task.Delay(1000);
            try
            {
              await StartDialogTask();
            }
            catch { }
          }
        });

    _ = Task.Run(async () =>
    {
      while (true)
      {
        await Task.Delay(1000);
        try
        {
          await SendJsonToLine();
        }
        catch { }
      }
    });

    _ = Task.Run(QueueManager.MonitorDialogActivity);

    botClient.StartReceiving(BotAsync.HandleUpdateAsync, BotAsync.HandleErrorAsync, receiverOptions, cancellationToken);
    Substitution.WriteLog("Start", $"Бот {botClient.GetMeAsync().Result.FirstName} запущен.");

    await Task.Delay(Timeout.Infinite);
  }

  public static async Task EndDayTask()
  {
    while (true)
    {
      await Substitution.DelayToTime(new TimeOnly(3, 30, 0));
      await QueueManager.ClearAllQueuesAsync();
    }
  }

  public static async Task StartDialogTask()
  {
    var readyQueueKeys = QueueManager.ReadyQueue.Keys.ToList();
    var questionQueueKeys = QueueManager.QuestionQueue.Keys.ToList();

    if (readyQueueKeys.Any() && questionQueueKeys.Any())
    {
      int minReadyId = readyQueueKeys.Min();
      int minQuestionId = questionQueueKeys.Min();

      var readyRecord = QueueManager.ReadyQueue[minReadyId];
      var questionRecord = QueueManager.QuestionQueue[minQuestionId];

      await QueueManager.RemoveFromReadyQueueAsync(readyRecord.ChatId);
      await QueueManager.RemoveFromQuestionQueueAsync(questionRecord.ChatId);


      UsersList.First(x => x.ChatId == questionRecord.ChatId).CurrentMode = Substitution.ModeCode["in dialog"];
      await botClient.SendTextMessageAsync(questionRecord.ChatId,
          $"На твой вопрос отвечает {readyRecord.FIO}",
          replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog"]));

      UsersList.First(x => x.ChatId == readyRecord.ChatId).CurrentMode = Substitution.ModeCode["in dialog rg"];
      await botClient.SendTextMessageAsync(readyRecord.ChatId,
          $"Вопрос от {questionRecord.FIO}",
          replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog rg"]));
      await botClient.CopyMessageAsync(readyRecord.ChatId, questionRecord.ChatId, questionRecord.StartMessageId);

      var dialogRecord = new DialogChatRecord
      {
        ChatIdEmployee = questionRecord.ChatId,
        ChatIdSupervisor = readyRecord.ChatId,
        FIOEmployee = questionRecord.FIO,
        FIOSupervisor = readyRecord.FIO,
        TimeStart = DateTime.UtcNow,
        TimeLast = DateTime.UtcNow,
        MessageHistory = [(questionRecord.ChatId, questionRecord.StartMessageId)]
      };

      await QueueManager.AddToDialogQueueAsync(dialogRecord);
    }
  }

  public static async Task SendJsonToLine()
  {
    var readyQueueJson = QueueManager.ReadyQueue.Select(record =>
        new
        {
          id = record.Key,
          name = record.Value.FIO,
          status = "READY",
          time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
        }).ToList();

    var awaitQueueJson = QueueManager.AwaitQueue.Select(record =>
        new
        {
          id = record.Key,
          name = record.Value.FIO,
          status = "FINISHING",
          time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
        }).ToList();

    var dialogQueueJson = QueueManager.DialogQueue.Select(record =>
        new
        {
          id = record.Key,
          name = record.Value.FIOSupervisor,
          status = "IN_DIALOG",
          time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
        }).ToList();

    var questionQueueJson = QueueManager.QuestionQueue.Select(record =>
        new
        {
          id = record.Key,
          name = record.Value.FIO,
          status = "AWAIT_ANSWER",
          time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
        }).ToList();

    var allRecordsJson = readyQueueJson.ToList();
    allRecordsJson.AddRange(awaitQueueJson);
    allRecordsJson.AddRange(dialogQueueJson);
    allRecordsJson.AddRange(questionQueueJson);

    var json = JsonConvert.SerializeObject(allRecordsJson);

    await Substitution.SendJsonToUrl("http://46.146.231.248/apinck", json);
  }
}