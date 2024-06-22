using Newtonsoft.Json;
using QuestionBot.Data;
using QuestionBot.Data.QueueModels;
using Telegram.Bot;
using Telegram.Bot.Requests;
using Telegram.Bot.Types.Enums;
using static QuestionBot.Program;

namespace QuestionBot.Async;

public class TasksAsync
{
  public static async Task EndDayTask()
  {
    while (true)
    {
      await Substitution.DelayToTime(new TimeOnly(3, 30, 0));
      await QueueManager.ClearQuestionQueuesAsync();
    }
  }

  public static async Task MergeDialogTask()
  {
    var questionQueueKeys = QueueManager.QuestionQueue.Keys.ToList();
    var dialogCount = QueueManager.DialogChats.Count();

    if (questionQueueKeys.Any() && (dialogCount < Config.QuestionQueueCount || Config.QuestionQueueCount == 0))
    {
      int minQuestionId = questionQueueKeys.Min();
      var questionRecord = QueueManager.QuestionQueue[minQuestionId];

      await QueueManager.RemoveFromQuestionQueueAsync(questionRecord.ChatId);

      UsersList.First(x => x.ChatId == questionRecord.ChatId).CurrentMode = Substitution.ModeCode["in dialog"];
      await botClient.SendMessageAsync(
         new SendMessageRequest()
         {
           ChatId = questionRecord.ChatId,
           Text = $"Вопрос передан на рассмотрение",
           ReplyMarkup = Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog"])
         });

      await QueueManager.AddDialogAsync(questionRecord);
    }
  }

  //   public static async Task SendJsonToLine()
  //   {
  //     var readyQueueJson = QueueManager.ReadyQueue.Select(record =>
  //         new
  //         {
  //           id = record.Key,
  //           name = record.Value.FIO,
  //           status = "READY",
  //           time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
  //         }).ToList();

  //     var dialogQueueJson = QueueManager.DialogQueue.Select(record =>
  //         new
  //         {
  //           id = record.Key,
  //           name = record.Value.FIOSupervisor,
  //           status = "IN_DIALOG",
  //           time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
  //         }).ToList();

  //     var questionQueueJson = QueueManager.QuestionQueue.Select(record =>
  //         new
  //         {
  //           id = record.Key,
  //           name = record.Value.FIO,
  //           status = "AWAIT_ANSWER",
  //           time = $"{(int)(DateTime.UtcNow - record.Value.TimeStart).TotalMinutes}:{(DateTime.UtcNow - record.Value.TimeStart).Seconds}"
  //         }).ToList();

  //     var allRecordsJson = readyQueueJson.ToList();
  //     allRecordsJson.AddRange(dialogQueueJson);
  //     allRecordsJson.AddRange(questionQueueJson);

  //     var json = JsonConvert.SerializeObject(allRecordsJson);
  // #if НЦК
  //     await Substitution.SendJsonToUrl("http://46.146.231.248/apinck", json);
  // #else
  //     await Substitution.SendJsonToUrl("http://185.255.135.17/apispsk", json);
  // #endif
  //   }
}
