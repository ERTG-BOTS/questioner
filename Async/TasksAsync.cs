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

    if (questionQueueKeys.Any() && (dialogCount < Config.DialogMaxCount || Config.DialogMaxCount == 0))
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
}
