using Newtonsoft.Json;
using QuestionBot.Data;
using QuestionBot.Data.QueueModels;
using Telegram.Bot;
using static QuestionBot.Program;

namespace QuestionBot.Async;

public class TasksAsync
{
  public static async Task EndDayTask()
  {
    while (true)
    {
      await Substitution.DelayToTime(new TimeOnly(3, 30, 0));
      await QueueManager.ClearAllQueuesAsync();
    }
  }

  public static async Task MergeDialogTask()
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
#if НЦК
    await Substitution.SendJsonToUrl("http://46.146.231.248/apinck", json);
#else
    await Substitution.SendJsonToUrl("http://46.146.231.248/apispsk", json);
#endif
  }
}
