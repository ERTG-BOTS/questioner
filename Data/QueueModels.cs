using System.Collections.Concurrent;
using Telegram.Bot;
using static QuestionBot.Program;

namespace QuestionBot.Data.QueueModels;

public class QuestionChatRecord
{
  public long ChatId { get; set; }
  public required string FIO { get; set; }
  public DateTime TimeStart { get; set; }
  public int StartMessageId { get; set; }
}

public class ReadyChatRecord
{
  public long ChatId { get; set; }
  public required string FIO { get; set; }
  public DateTime TimeStart { get; set; }
}

public class DialogChatRecord
{
  public long ChatIdEmployee { get; set; }
  public required string FIOEmployee { get; set; }
  public long ChatIdSupervisor { get; set; }
  public required string FIOSupervisor { get; set; }
  public DateTime TimeStart { get; set; }
  public DateTime TimeLast { get; set; }
  public required List<(long ChatId, int MessageId)> MessageHistory { get; set; }
}

public class QueueChatManager
{
  private readonly SemaphoreSlim questionQueueSemaphore = new(1, 1);
  private readonly SemaphoreSlim readyQueueSemaphore = new(1, 1);
  private readonly SemaphoreSlim dialogQueueSemaphore = new(1, 1);
  private readonly SemaphoreSlim awaitQueueSemaphore = new(1, 1);

  public ConcurrentDictionary<int, DialogChatRecord> DialogQueue { get; private set; }
  public ConcurrentDictionary<int, QuestionChatRecord> QuestionQueue { get; private set; }
  public ConcurrentDictionary<int, ReadyChatRecord> ReadyQueue { get; private set; }
  public ConcurrentDictionary<int, ReadyChatRecord> AwaitQueue { get; private set; }

  public QueueChatManager()
  {
    DialogQueue = new ConcurrentDictionary<int, DialogChatRecord>();
    QuestionQueue = new ConcurrentDictionary<int, QuestionChatRecord>();
    ReadyQueue = new ConcurrentDictionary<int, ReadyChatRecord>();
    AwaitQueue = new ConcurrentDictionary<int, ReadyChatRecord>();
  }

  public async Task<bool> AddToQuestionQueueAsync(QuestionChatRecord record)
  {
    await questionQueueSemaphore.WaitAsync();
    try
    {
      record.TimeStart = DateTime.UtcNow;
      int id = !QuestionQueue.IsEmpty ? QuestionQueue.Keys.Max() + 1 : 1;
      QuestionQueue.TryAdd(id, record);
      return true;
    }
    finally
    {
      questionQueueSemaphore.Release();
    }
  }

  public async Task<bool> RemoveFromQuestionQueueAsync(long chatId)
  {
    await questionQueueSemaphore.WaitAsync();
    try
    {
      var removedRecord = QuestionQueue.FirstOrDefault(x => x.Value.ChatId == chatId);
      if (!removedRecord.Equals(default(KeyValuePair<int, QuestionChatRecord>)))
      {
        QuestionQueue.TryRemove(removedRecord.Key, out _);
        var remainingRecords = QuestionQueue.Values.ToList();
        QuestionQueue.Clear();
        for (int i = 0; i < remainingRecords.Count; i++)
        {
          QuestionQueue.TryAdd(i + 1, remainingRecords[i]);
        }
        return true;
      }
      return false;
    }
    finally
    {
      questionQueueSemaphore.Release();
    }
  }

  public async Task<bool> AddToAwaitQueueAsync(ReadyChatRecord record)
  {
    await awaitQueueSemaphore.WaitAsync();
    try
    {
      record.TimeStart = DateTime.UtcNow;
      int id = !AwaitQueue.IsEmpty ? QuestionQueue.Keys.Max() + 1 : 1;
      AwaitQueue.TryAdd(id, record);
      return true;
    }
    finally
    {
      awaitQueueSemaphore.Release();
    }
  }

  public async Task<bool> RemoveFromAwaitQueueAsync(long chatId)
  {
    await awaitQueueSemaphore.WaitAsync();
    try
    {
      var removedRecord = AwaitQueue.FirstOrDefault(x => x.Value.ChatId == chatId);
      if (!removedRecord.Equals(default(KeyValuePair<int, ReadyChatRecord>)))
      {
        AwaitQueue.TryRemove(removedRecord.Key, out _);
        var remainingRecords = AwaitQueue.Values.ToList();
        AwaitQueue.Clear();
        for (int i = 0; i < remainingRecords.Count; i++)
        {
          AwaitQueue.TryAdd(i + 1, remainingRecords[i]);
        }
        return true;
      }
      return false;
    }
    finally
    {
      awaitQueueSemaphore.Release();
    }
  }

  public async Task<bool> AddToReadyQueueAsync(ReadyChatRecord record)
  {
    await readyQueueSemaphore.WaitAsync();
    try
    {
      record.TimeStart = DateTime.UtcNow;
      int id = !ReadyQueue.IsEmpty ? ReadyQueue.Keys.Max() + 1 : 1;
      ReadyQueue.TryAdd(id, record);
      return true;
    }
    finally
    {
      readyQueueSemaphore.Release();
    }
  }

  public async Task<bool> RemoveFromReadyQueueAsync(long chatId)
  {
    await readyQueueSemaphore.WaitAsync();
    try
    {
      var removedRecord = ReadyQueue.FirstOrDefault(x => x.Value.ChatId == chatId);
      if (!removedRecord.Equals(default(KeyValuePair<int, ReadyChatRecord>)))
      {
        ReadyQueue.TryRemove(removedRecord.Key, out _);
        var remainingRecords = ReadyQueue.Values.ToList();
        ReadyQueue.Clear();
        for (int i = 0; i < remainingRecords.Count; i++)
        {
          ReadyQueue.TryAdd(i + 1, remainingRecords[i]);
        }
        return true;
      }
      return false;
    }
    finally
    {
      readyQueueSemaphore.Release();
    }
  }

  public async Task<bool> AddToDialogQueueAsync(DialogChatRecord record)
  {
    await dialogQueueSemaphore.WaitAsync();
    try
    {
      record.TimeStart = DateTime.UtcNow;
      int id = !DialogQueue.IsEmpty ? DialogQueue.Keys.Max() + 1 : 1;
      DialogQueue.TryAdd(id, record);
      return true;
    }
    finally
    {
      dialogQueueSemaphore.Release();
    }
  }

  public async Task AddToMessageHistoryAsync(long chatId, int messageId)
  {
    await dialogQueueSemaphore.WaitAsync();
    try
    {
      var dialogRecord = DialogQueue.FirstOrDefault(x => x.Value.ChatIdEmployee == chatId || x.Value.ChatIdSupervisor == chatId).Value;
      if (dialogRecord != null)
      {
        long targetChatId = dialogRecord.ChatIdEmployee == chatId ? dialogRecord.ChatIdSupervisor : dialogRecord.ChatIdEmployee;
        try
        {
          await botClient.CopyMessageAsync(targetChatId, chatId, messageId);
          dialogRecord.MessageHistory ??= [];
          dialogRecord.MessageHistory.Add((chatId, messageId));
          dialogRecord.TimeLast = DateTime.UtcNow;
          Substitution.WriteLog("Диалог", $"\x1b[94m{chatId}\x1b[0m отправляет сообщение => \x1b[93m{targetChatId}\x1b[0m");
        }
        catch (Exception)
        {
          await botClient.SendTextMessageAsync(chatId, "Ошибка отправки");
        }
      }
    }
    finally
    {
      dialogQueueSemaphore.Release();
    }
  }

  private async Task SendMessageDialogRemove(DialogChatRecord dialog, string token)
  {
    UsersList.First(x => x.ChatId == dialog.ChatIdEmployee).CurrentMode = Substitution.ModeCode["signed"];
    await botClient.SendTextMessageAsync(dialog.ChatIdEmployee,
        "Диалог завершен",
        replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["signed"]));
    await botClient.SendTextMessageAsync(dialog.ChatIdEmployee,
        $"Оцени диалог с {dialog.FIOSupervisor}",
        replyMarkup: Keyboards.DialogQuality(token));

    UsersList.First(x => x.ChatId == dialog.ChatIdSupervisor).CurrentMode = Substitution.ModeCode["await ready rg"];
    await botClient.SendTextMessageAsync(dialog.ChatIdSupervisor,
        "Диалог завершен",
        replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["await ready rg"]));

    Task delayAfter = Task.Run(async () =>
    {
      await botClient.SendTextMessageAsync(dialog.ChatIdSupervisor,
          $"Ожидание после завершения диалога {Config.DelayAfterDialog} секунд");
      await QueueManager.AddToAwaitQueueAsync(new ReadyChatRecord()
      {
        ChatId = dialog.ChatIdSupervisor,
        FIO = dialog.FIOSupervisor,
        TimeStart = DateTime.UtcNow
      });
      await Task.Delay(Config.DelayAfterDialog);
      var user = UsersList.First(x => x.ChatId == dialog.ChatIdSupervisor);
      if (user.CurrentMode == Substitution.ModeCode["await ready rg"])
      {
        await QueueManager.RemoveFromAwaitQueueAsync(dialog.ChatIdSupervisor);
        user.CurrentMode = Substitution.ModeCode["ready rg"];
        await QueueManager.AddToReadyQueueAsync(new ReadyChatRecord()
        {
          ChatId = dialog.ChatIdSupervisor,
          FIO = dialog.FIOSupervisor,
          TimeStart = DateTime.UtcNow
        });
        await botClient.SendTextMessageAsync(dialog.ChatIdSupervisor,
            "Теперь ты готов",
            replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["ready rg"]));
      }
    });
  }

  public async Task<bool> EndDialogAsync(long chatId)
  {
    await dialogQueueSemaphore.WaitAsync();
    try
    {
      var removedRecord = DialogQueue.FirstOrDefault(x => x.Value.ChatIdEmployee == chatId || x.Value.ChatIdSupervisor == chatId);
      if (!removedRecord.Equals(default(KeyValuePair<int, DialogChatRecord>)))
      {
        DialogQueue.TryRemove(removedRecord.Key, out var dialogRecord);
        if (dialogRecord != null)
        {
          string tokenDialog = Guid.NewGuid().ToString();
          string dialogHistory = string.Join("@", dialogRecord.MessageHistory.Select(m => $"{m.ChatId}#{m.MessageId}"));

          var dialogHistoryModel = new Models.DialogHistoryModels
          {
            TokenDialog = tokenDialog,
            FIOEmployee = dialogRecord.FIOEmployee,
            FIOSupervisor = dialogRecord.FIOSupervisor,
            TimeDialogStart = dialogRecord.TimeStart,
            TimeDialogEnd = dialogRecord.TimeLast,
            DialogQuality = null,
            DialogHistory = dialogHistory
          };
          using (AppDbContext dbContext = new())
          {
            dbContext.DialogHistoryModels.Add(dialogHistoryModel);
            await dbContext.SaveChangesAsync();
          }

          _ = Task.Run(() => SendMessageDialogRemove(dialogRecord, tokenDialog));

          var remainingRecords = DialogQueue.Values.ToList();
          DialogQueue.Clear();
          for (int i = 0; i < remainingRecords.Count; i++)
          {
            DialogQueue.TryAdd(i + 1, remainingRecords[i]);
          }

          return true;
        }
      }
      return false;
    }
    finally
    {
      dialogQueueSemaphore.Release();
    }
  }

  public async Task MonitorDialogActivity()
  {
    while (true)
    {
      var currentTime = DateTime.UtcNow;
      var dialogsToEnd = new List<int>();

      foreach (var dialog in DialogQueue)
      {
        var timeSinceLastMessage = currentTime - dialog.Value.TimeLast;
        if (timeSinceLastMessage.TotalMinutes >= 3)
        {
          dialogsToEnd.Add(dialog.Key);
        }
        else if (timeSinceLastMessage.Minutes == 2 && timeSinceLastMessage.Seconds <= 10)
        {
          await botClient.SendTextMessageAsync(dialog.Value.ChatIdEmployee, "Диалог будет завершен из-за отсутствия активности");
          await botClient.SendTextMessageAsync(dialog.Value.ChatIdSupervisor, "Диалог будет завершен из-за отсутствия активности");
        }
      }

      foreach (var dialogId in dialogsToEnd)
      {
        var dialog = DialogQueue[dialogId];
        await botClient.SendTextMessageAsync(dialog.ChatIdEmployee, "Диалог завершен из-за отсутствия активности");
        await botClient.SendTextMessageAsync(dialog.ChatIdSupervisor, "Диалог завершен из-за отсутствия активности");
        await QueueManager.EndDialogAsync(dialog.ChatIdEmployee);
      }

      await Task.Delay(10000);
    }
  }

  public async Task ClearAllQueuesAsync()
  {
    var readyQueueItems = ReadyQueue.Values.ToList();
    var awaitQueueItems = AwaitQueue.Values.ToList();
    var questionQueueItems = QuestionQueue.Values.ToList();

    foreach (var item in readyQueueItems)
    {
      await botClient.SendTextMessageAsync(item.ChatId, "Твой статус изменен на \"Не готов\"");
    }
    ReadyQueue.Clear();

    foreach (var item in awaitQueueItems)
    {
      await botClient.SendTextMessageAsync(item.ChatId, "Твой статус изменен на \"Не готов\"");
    }
    AwaitQueue.Clear();

    foreach (var item in questionQueueItems)
    {
      await botClient.SendTextMessageAsync(item.ChatId, "Твой вопрос был отменен");
    }
    QuestionQueue.Clear();
  }
}