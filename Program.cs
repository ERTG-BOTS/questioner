using System.Globalization;
using OfficeOpenXml;
using QuestionBot.Async;
using QuestionBot.Data;
using QuestionBot.Data.Models;
using QuestionBot.Data.QueueModels;
using Telegram.Bot;
using Telegram.Bot.Polling;
using static QuestionBot.Async.TasksAsync;

namespace QuestionBot;

public class Program
{
    public static List<UserModel> UsersList = [];
    public static readonly ConfigInfo Config = new();
    public static ITelegramBotClient botClient = new TelegramBotClient(Config.BotToken);
    public static QueueChatManager QueueManager = new();
    public static readonly CultureInfo russianCulture = new("ru-RU");

    private static bool TryConnectAllTable()
    {
        using var db = new AppDbContext();
        return !db.TryConnectAllTable();
    }

    private static async Task Main()
    {
        ExcelPackage.LicenseContext = LicenseContext.NonCommercial;

        var botInfo = await botClient.GetMe();
        Substitution.WriteLog("Start", $"Загрузка бота {botInfo.FirstName}...");
        var bufferDirectory = Path.Combine($"{AppContext.BaseDirectory}", "buffer");

        if (!Directory.Exists(bufferDirectory)) Directory.CreateDirectory(bufferDirectory);

        CancellationTokenSource cts = new();
        var cancellationToken = cts.Token;
        ReceiverOptions receiverOptions = new();

        Config.BotChatId = botInfo.Id;
        Config.PrintAllSettings();

        if (TryConnectAllTable()) Environment.Exit(999);


        _ = Task.Run(async () =>
        {
            while (true)
            {
                await Task.Delay(1000);
                try
                {
                    await MergeDialogTask();
                }
                catch
                {
                }
            }
        });

        _ = Task.Run(EndDayTask);

        _ = Task.Run(RemoveOldTopics);
        
        _ = Task.Run(async () =>
        {
            while (true)
            {
                await Task.Delay(60 * 1000);
                try
                {
                    await ExpirationOverwatchTask();
                }
                catch
                {
                }
            }
        });

        botClient.StartReceiving(BotAsync.HandleUpdateAsync, BotAsync.HandleErrorAsync, receiverOptions,
            cancellationToken);
        Substitution.WriteLog("Start", $"Бот {botInfo.FirstName} запущен.");

        await Task.Delay(Timeout.Infinite);
    }
}