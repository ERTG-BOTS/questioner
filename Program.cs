using System.Globalization;
using Newtonsoft.Json;
using QuestionBot.Data;
using QuestionBot.Data.QueueModels;
using QuestionBot.Async;
using Telegram.Bot;
using Telegram.Bot.Polling;
using OfficeOpenXml;
using static QuestionBot.Async.TasksAsync;

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
    ExcelPackage.LicenseContext = LicenseContext.NonCommercial;

    botClient = new TelegramBotClient(Config.BotToken);
    Substitution.WriteLog("Start", $"Загрузка бота {botClient.GetMeAsync().Result.FirstName}...");
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

    Config.PrintAllSettings();

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

    _ = Task.Run(EndDayTask);

    botClient.StartReceiving(BotAsync.HandleUpdateAsync, BotAsync.HandleErrorAsync, receiverOptions, cancellationToken);
    Substitution.WriteLog("Start", $"Бот {botClient.GetMeAsync().Result.FirstName} запущен.");

    await Task.Delay(Timeout.Infinite);
  }
}