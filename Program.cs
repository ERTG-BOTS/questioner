using System.Globalization;
using QuestionBot.Data;
using QuestionBot.Data.QueueModels;
using QuestionBot.Async;
using Telegram.Bot;
using Telegram.Bot.Polling;
using OfficeOpenXml;
using static QuestionBot.Async.TasksAsync;
using Telegram.Bot.Requests;
using System.Security.Cryptography;

namespace QuestionBot;

public class Program
{
  public static ITelegramBotClient botClient = new TelegramBotClient("");
  public static List<Data.Models.UserModel> UsersList = [];
  public static ConfigInfo Config = new();
  public static QueueChatManager QueueManager = new();
  public static readonly CultureInfo russianCulture = new("ru-RU");
  private static bool TryConnectAllTable()
  {
    using var db = new AppDbContext();
    return !db.TryConnectAllTable();
  }
  static async Task Main()
  {
    ExcelPackage.LicenseContext = LicenseContext.NonCommercial;

    botClient = new TelegramBotClient(Config.BotToken);
    var botInfo = botClient.MakeRequestAsync(new GetMeRequest()).Result;
    Substitution.WriteLog("Start", $"Загрузка бота {botInfo.FirstName}...");
    var bufferDirectory = Path.Combine($"{AppContext.BaseDirectory}", "buffer");

    if (!Directory.Exists(bufferDirectory))
    {
      Directory.CreateDirectory(bufferDirectory);
    }

    CancellationTokenSource cts = new();
    CancellationToken cancellationToken = cts.Token;
    ReceiverOptions receiverOptions = new()
    {
      AllowedUpdates = { },
    };

    Config.BotChatId = botInfo.Id;
    Config.PrintAllSettings();

    if (TryConnectAllTable())
    {
      Environment.Exit(999);
    }


    _ = Task.Run(async () =>
        {
          while (true)
          {
            await Task.Delay(1000);
            try
            {
              await MergeDialogTask();
            }
            catch { }
          }
        });

    _ = Task.Run(EndDayTask);

    _ = Task.Run(async () =>
    {
      while (true)
      {
          await Task.Delay(60 * 1000);
        try
        {
          await ExpirationOverwatchTask();
        } catch {}
      }
    });

    botClient.StartReceiving(BotAsync.HandleUpdateAsync, BotAsync.HandleErrorAsync, receiverOptions, cancellationToken);
    Substitution.WriteLog("Start", $"Бот {botInfo.FirstName} запущен.");

    await Task.Delay(Timeout.Infinite);
  }
}