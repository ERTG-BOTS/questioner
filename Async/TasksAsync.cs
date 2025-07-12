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
      await botClient.SendMessage(
           chatId: questionRecord.ChatId,
           text: $"Вопрос передан на рассмотрение",
           replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog"])
         );

      await QueueManager.AddDialogAsync(questionRecord);
    }
  }

  public static async Task ExpirationOverwatchTask()
  {
    DateTime utcNow = DateTime.UtcNow;
    foreach (var dialog in QueueManager.DialogChats.Where(x => x.LastMessageReceived != null && utcNow.Subtract((DateTime)x.LastMessageReceived).TotalMinutes > 2))
    {
      if (utcNow.Subtract((DateTime)dialog.LastMessageReceived!).TotalMinutes > 3)
      {
        await botClient.SendMessage(
          chatId: dialog.ChatIdEmployee,
          text: "Чат был неактивен в течение 3 минут и сейчас будет закрыт"
        );

        await botClient.SendMessage(
          chatId: Config.ForumId,
          messageThreadId: dialog.MessageThreadId,
          text: "Чат был неактивен в течение 3 минут и сейчас будет закрыт"
        );

        await QueueManager.EndDialogAsync(dialog);
      }
      else
      {

        await botClient.SendMessage(
          chatId: dialog.ChatIdEmployee,
          text: "Чат был неактивен в течение 2 минут. Он закроется через минуту если не будет активности. Если вопрос неактуален, закройте диалог."
        );

        await botClient.SendMessage(
          chatId: Config.ForumId,
          messageThreadId: dialog.MessageThreadId,
          text: "Чат был неактивен в течение 2 минут. Он закроется через минуту если не будет активности. Если вопрос неактуален, закройте диалог."
        );

      }
    }
  }
}
