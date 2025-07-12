using System.Collections.Concurrent;
using Telegram.Bot;
using Telegram.Bot.Requests;
using Telegram.Bot.Types;
using static QuestionBot.Program;

namespace QuestionBot.Data.QueueModels;

public class QuestionChatRecord
{
  public long ChatId { get; set; }
  public required string FIO { get; set; }
  public DateTime TimeStart { get; set; }
  public int StartMessageId { get; set; }
}

public class DialogChatRecord
{
  public required string Token { get; set; }
  public required string FIOEmployee { get; set; }
  public required long ChatIdEmployee { get; set; }
  public required List<string> ListFIOSupervisor { get; set; }
  public required long ChatIdLastSupervisor { get; set; }
  public required string StartQuestion { get; set; }
  public required int FirstMessageId { get; set; }
  public int MessageThreadId { get; set; }
  public required List<string> ListStartDialog { get; set; }
  public required List<string> ListEndDialog { get; set; }
  public DateTime? LastMessageReceived { get; set; }

}

public class QueueChatManager
{
  public readonly SemaphoreSlim questionQueueSemaphore = new(1, 1);
  public readonly SemaphoreSlim dialogSemaphore = new(1, 1);

  public ConcurrentDictionary<int, QuestionChatRecord> QuestionQueue { get; private set; }
  public List<DialogChatRecord> DialogChats { get; private set; }

  public QueueChatManager()
  {
    QuestionQueue = new ConcurrentDictionary<int, QuestionChatRecord>();
    DialogChats = [];
  }

  public async Task<bool> AddToQuestionQueueAsync(QuestionChatRecord record)
  {
    await questionQueueSemaphore.WaitAsync();
    try
    {
      record.TimeStart = DateTime.UtcNow.AddHours(3);
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

  public async Task ClearQuestionQueuesAsync()
  {
    var questionQueueItems = QuestionQueue.Values.ToList();

    foreach (var item in questionQueueItems)
    {
      await botClient.SendMessage(
              chatId: item.ChatId,
              text: "Твой вопрос был отменен"
            );
    }
    QuestionQueue.Clear();
  }

  public async Task AddDialogAsync(Models.DialogHistories dialog, long chatId)
  {
    await Task.Delay(5000);
    await dialogSemaphore.WaitAsync();
    try
    {
      DialogChats.Add(new DialogChatRecord()
      {
        Token = dialog.Token,
        FIOEmployee = dialog.FIOEmployee,
        ChatIdEmployee = chatId,
        ListFIOSupervisor = [.. dialog.ListFIOSupervisor.Split(";")],
        ChatIdLastSupervisor = 0,
        StartQuestion = dialog.StartQuestion,
        FirstMessageId = dialog.FirstMessageId,
        MessageThreadId = dialog.MessageThreadId,
        ListStartDialog = [.. dialog.ListStartDialog.Split(";")],
        ListEndDialog = [.. dialog.ListEndDialog.Split(";")],
        LastMessageReceived = DateTime.UtcNow,
      });

      await botClient.ReopenForumTopic(
                        chatId: Config.ForumId,
                        messageThreadId: dialog.MessageThreadId
                      );

      await botClient.EditForumTopic(
          chatId: Config.ForumId,
          messageThreadId: dialog.MessageThreadId,
          name: dialog.FIOEmployee,
          iconCustomEmojiId: Substitution.EmojiKeys["new"]
        );

      await botClient.SendMessage(
          chatId: Config.ForumId,
          messageThreadId: dialog.MessageThreadId,
          text: "Диалог возобновлен"
        );

      UsersList.First(x => x.ChatId == chatId).CurrentMode = Substitution.ModeCode["in dialog"];

      await botClient.SendMessage(
          chatId: chatId,
          text: "Диалог возобновлен",
          replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog"])
        );
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }

  public async Task AddDialogAsync(QuestionChatRecord question)
  {
    await dialogSemaphore.WaitAsync();
    try
    {
      var newTopic = await botClient.CreateForumTopic(
                              chatId: Config.ForumId,
                              name: question.FIO
                            );

      await botClient.CloseForumTopic(
          chatId: Config.ForumId,
          messageThreadId: newTopic.MessageThreadId
      );

      await botClient.EditForumTopic(
          chatId: Config.ForumId,
          messageThreadId: newTopic.MessageThreadId,
          iconCustomEmojiId: Substitution.EmojiKeys["new"]
        );

      var user = Models.UserModel.GetUser(chatId: question.ChatId);

      string text;
      if (user != null)
      {
        text = $"Вопрос задает <b>{question.FIO}</b> (@{user.Username})\n\n" +
                   $"<i>РГ: <b>{user.Boss}</b></i>";
      }
      else
      {
        text = $"Вопрос задает <b>{question.FIO}</b>";
      }
      
      await botClient.SendMessage(
          chatId: Config.ForumId,
          text: text,
          messageThreadId: newTopic.MessageThreadId,
          parseMode: Telegram.Bot.Types.Enums.ParseMode.Html
      );

      var firstMessageId = await botClient.CopyMessage(
          chatId: Config.ForumId,
          messageThreadId: newTopic.MessageThreadId,
          fromChatId: question.ChatId,
          messageId: question.StartMessageId
      );

      var dialogRecord = new DialogChatRecord()
      {
        Token = Guid.NewGuid().ToString(),
        FIOEmployee = question.FIO,
        ChatIdEmployee = question.ChatId,
        FirstMessageId = firstMessageId.Id,
        StartQuestion = question.TimeStart.ToString("dd.MM.yyyy HH:mm:ss"),
        MessageThreadId = newTopic.MessageThreadId,
        ListFIOSupervisor = [],
        ChatIdLastSupervisor = 0,
        ListStartDialog = [],
        ListEndDialog = [],
        LastMessageReceived = DateTime.UtcNow,
      };

      DialogChats.Add(dialogRecord);
      
      await botClient.ReopenForumTopic(
          chatId: Config.ForumId,
          messageThreadId: newTopic.MessageThreadId
      );
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }

  private async Task ErrorDialogAsync(long chatId)
  {
    await botClient.SendMessage(
        chatId: chatId,
        text: "Диалог не был найден\nСоздай вопрос снова"
    );
    var user = UsersList.FirstOrDefault(x => x.ChatId == chatId);
    if (user != null)
      user.CurrentMode = user.DefaultMode;
  }

  public async Task DeliveryMessageDialogAsync(DialogChatRecord dialog, int messageId)
  {
    await dialogSemaphore.WaitAsync();
    try
    {
      await Task.Delay(1000);
      var dialogRecord = DialogChats.FirstOrDefault(x => x == dialog);
      if (dialogRecord != null)
      {
        await botClient.CopyMessage(
            chatId: dialogRecord.ChatIdEmployee,
            fromChatId: Config.ForumId,
            messageId: messageId
        );
        dialogRecord.LastMessageReceived = DateTime.UtcNow;
      }
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }

  public async Task DeliveryMessageDialogAsync(long chatId, int messageId)
  {
    await dialogSemaphore.WaitAsync();
    try
    {
      await Task.Delay(1000);
      var dialogRecord = DialogChats.FirstOrDefault(x => x.ChatIdEmployee == chatId);
      if (dialogRecord != null)
      {
        await botClient.CopyMessage(
            chatId: Config.ForumId,
            messageThreadId: dialogRecord.MessageThreadId,
            fromChatId: dialogRecord.ChatIdEmployee,
            messageId: messageId
        );
        dialogRecord.LastMessageReceived = DateTime.UtcNow;
      }
      else
      {
        await ErrorDialogAsync(chatId);
      }
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }

  public async Task EndDialogAsync(DialogChatRecord dialog)
  {
    await dialogSemaphore.WaitAsync();
    try
    {
      var dialogRecord = DialogChats.FirstOrDefault(x => x == dialog);

      if (dialogRecord != null)
      {
        if (dialogRecord.ListStartDialog.Count != 0)
          using (var db = new AppDbContext())
          {
            var dialogHistoryRecord = db.DialogHistory.FirstOrDefault(x => x.Token == dialogRecord.Token);
            dialogRecord.ListEndDialog.Add(Substitution.GetCorrectDateTime);
            if (dialogHistoryRecord == null)
            {
              dialogHistoryRecord = Models.DialogHistories.GetDialogHistories(dialogRecord);
              db.DialogHistory.Add(dialogHistoryRecord);
              db.SaveChanges();
            }
            else
            {
              var newDialogHistoryRecord = Models.DialogHistories.GetDialogHistories(dialogRecord);
              if (dialogHistoryRecord != newDialogHistoryRecord)
              {
                dialogHistoryRecord.ListFIOSupervisor = string.Join(";", dialogRecord.ListFIOSupervisor);
                dialogHistoryRecord.ListStartDialog = string.Join(";", dialogRecord.ListStartDialog);
                dialogHistoryRecord.ListEndDialog = string.Join(";", dialogRecord.ListEndDialog);
                db.DialogHistory.Update(dialogHistoryRecord);
                db.SaveChanges();
              }
            }
          }
        DialogChats.Remove(dialogRecord);
        await botClient.SendMessage(
            chatId: Config.ForumId,
            messageThreadId: dialogRecord.MessageThreadId,
            text: $"Диалог завершен" + (dialogRecord.ListStartDialog.Count == 0 ? " и будет удален" : "")
          );

        UsersList.First(x => x.ChatId == dialogRecord.ChatIdEmployee).CurrentMode = Substitution.ModeCode["signed"];
        await botClient.SendMessage(
            chatId: dialogRecord.ChatIdEmployee,
            text: $"Диалог завершен" + (dialogRecord.ListStartDialog.Count == 0 ? " и будет удален" : ""),
            replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["signed"])
          );

        if (dialogRecord.ListStartDialog.Count != 0)
        {
          await botClient.SendMessage(
              chatId: dialogRecord.ChatIdEmployee,
              text: $"Оцени диалог",
              replyMarkup: Keyboards.DialogQuality(dialogRecord.Token)
            );
          _ = Task.Run(async () =>
          {
            await Task.Delay(5000);
            await botClient.CloseForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId
              );

            await botClient.EditForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId,
                name: dialogRecord.Token,
                iconCustomEmojiId: Substitution.EmojiKeys["end"]
              );
          });
        }
        else
          _ = Task.Run(async () =>
          {
            await Task.Delay(5000);
            await botClient.DeleteForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId
              );
          });
      }
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }

  public async Task EndDialogAsync(long chatId)
  {
    await dialogSemaphore.WaitAsync();
    try
    {
      var dialogRecord = DialogChats.FirstOrDefault(x => x.ChatIdEmployee == chatId);

      if (dialogRecord != null)
      {
        if (dialogRecord.ListStartDialog.Count != 0)
          using (var db = new AppDbContext())
          {
            var dialogHistoryRecord = db.DialogHistory.FirstOrDefault(x => x.Token == dialogRecord.Token);
            if (dialogHistoryRecord == null)
            {
              dialogHistoryRecord = Models.DialogHistories.GetDialogHistories(dialogRecord);
              db.DialogHistory.Add(dialogHistoryRecord);
              db.SaveChanges();
            }
            else
            {
              var newDialogHistoryRecord = Models.DialogHistories.GetDialogHistories(dialogRecord);
              if (dialogHistoryRecord != newDialogHistoryRecord)
              {
                dialogRecord.ListEndDialog.Add(Substitution.GetCorrectDateTime);
                dialogHistoryRecord.ListFIOSupervisor = string.Join(";", dialogRecord.ListFIOSupervisor);
                dialogHistoryRecord.ListStartDialog = string.Join(";", dialogRecord.ListStartDialog);
                dialogHistoryRecord.ListEndDialog = string.Join(";", dialogRecord.ListEndDialog);
                db.DialogHistory.Update(dialogHistoryRecord);
                db.SaveChanges();
              }
            }
          }
        DialogChats.Remove(dialogRecord);
        await botClient.SendMessage(
            chatId: Config.ForumId,
            messageThreadId: dialogRecord.MessageThreadId,
            text: $"Диалог завершен" + (dialogRecord.ListStartDialog.Count == 0 ? " и будет удален" : "")
          );

        UsersList.First(x => x.ChatId == dialogRecord.ChatIdEmployee).CurrentMode = Substitution.ModeCode["signed"];
        await botClient.SendMessage(
            chatId: dialogRecord.ChatIdEmployee,
            text: $"Диалог завершен" + (dialogRecord.ListStartDialog.Count == 0 ? " и будет удален" : ""),
            replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["signed"])
          );

        if (dialogRecord.ListStartDialog.Count != 0)
        {
          await botClient.SendMessage(
              chatId: dialogRecord.ChatIdEmployee,
              text: $"Оцени диалог",
              replyMarkup: Keyboards.DialogQuality(dialogRecord.Token)
            );
          _ = Task.Run(async () =>
          {
            await Task.Delay(5000);
            await botClient.CloseForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId
              );

            await botClient.EditForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId,
                name: dialogRecord.Token,
                iconCustomEmojiId: Substitution.EmojiKeys["end"]
              );
          });
        }
        else
          _ = Task.Run(async () =>
          {
            await Task.Delay(5000);
            await botClient.DeleteForumTopic(
                chatId: Config.ForumId,
                messageThreadId: dialogRecord.MessageThreadId
              );
          });
      }
      else
      {
        await ErrorDialogAsync(chatId);
      }
    }
    finally
    {
      dialogSemaphore.Release();
    }
  }
}