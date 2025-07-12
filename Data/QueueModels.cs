using System.Collections.Concurrent;
using QuestionBot.Data.Models;
using Telegram.Bot;
using Telegram.Bot.Types.Enums;
using static QuestionBot.Program;

namespace QuestionBot.Data.QueueModels;

public class QuestionChatRecord
{
    public long ChatId { get; set; }
    public required string FIO { get; set; }
    public DateTime TimeStart { get; set; }
    public int StartMessageId { get; set; }
    public string CleverLink { get; set; }
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
    public required string CleverLink { get; set; }
    public DateTime? LastMessageReceived { get; set; }
}

public class QueueChatManager
{
    public readonly SemaphoreSlim dialogSemaphore = new(1, 1);
    public readonly SemaphoreSlim questionQueueSemaphore = new(1, 1);

    public QueueChatManager()
    {
        QuestionQueue = new ConcurrentDictionary<int, QuestionChatRecord>();
        DialogChats = [];
    }

    public ConcurrentDictionary<int, QuestionChatRecord> QuestionQueue { get; }
    public List<DialogChatRecord> DialogChats { get; }

    public async Task<bool> AddToQuestionQueueAsync(QuestionChatRecord record)
    {
        await questionQueueSemaphore.WaitAsync();
        try
        {
            record.TimeStart = DateTime.UtcNow.AddHours(3);
            var id = !QuestionQueue.IsEmpty ? QuestionQueue.Keys.Max() + 1 : 1;
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
                for (var i = 0; i < remainingRecords.Count; i++) QuestionQueue.TryAdd(i + 1, remainingRecords[i]);
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
            await botClient.SendMessage(
                item.ChatId,
                "Твой вопрос был отменен"
            );
        QuestionQueue.Clear();
    }

    public async Task AddDialogAsync(DialogHistories dialog, long chatId)
    {
        await Task.Delay(5000);
        await dialogSemaphore.WaitAsync();
        try
        {
            DialogChats.Add(new DialogChatRecord
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
                CleverLink = dialog.CleverLink
            });

            await botClient.ReopenForumTopic(
                Config.ForumId,
                dialog.MessageThreadId
            );

            await botClient.EditForumTopic(
                Config.ForumId,
                dialog.MessageThreadId,
                dialog.FIOEmployee,
                Substitution.EmojiKeys["new"]
            );

            await botClient.SendMessage(
                Config.ForumId,
                messageThreadId: dialog.MessageThreadId,
                text: "Диалог возобновлен"
            );

            UsersList.First(x => x.ChatId == chatId).CurrentMode = Substitution.ModeCode["in dialog"];

            await botClient.SendMessage(
                chatId,
                "Диалог возобновлен",
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
                Config.ForumId,
                question.FIO
            );

            await botClient.CloseForumTopic(
                Config.ForumId,
                newTopic.MessageThreadId
            );

            await botClient.EditForumTopic(
                Config.ForumId,
                newTopic.MessageThreadId,
                iconCustomEmojiId: Substitution.EmojiKeys["new"]
            );

            var user = UserModel.GetUser(question.ChatId);

            string text;
            if (user != null)
                text = $"Вопрос задает <b>{question.FIO}</b> (@{user.Username})\n\n" +
                       $"<b>🗃️ Регламент:</b> <a href='{question.CleverLink}'>тык</a>\n" +
                       $"<b>👑 РГ:</b> {user.Boss}";
            else
                text = $"Вопрос задает <b>{question.FIO}</b>";

            await botClient.SendMessage(
                Config.ForumId,
                text,
                messageThreadId: newTopic.MessageThreadId,
                parseMode: ParseMode.Html
            );

            var firstMessageId = await botClient.CopyMessage(
                Config.ForumId,
                messageThreadId: newTopic.MessageThreadId,
                fromChatId: question.ChatId,
                messageId: question.StartMessageId
            );

            var dialogRecord = new DialogChatRecord
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
                CleverLink = question.CleverLink
            };

            DialogChats.Add(dialogRecord);

            try
            {
                await botClient.ReopenForumTopic(
                    Config.ForumId,
                    newTopic.MessageThreadId
                );
            }
            catch (Exception ex)
            {
                Substitution.WriteLog("Error", "Ошибка при открытии топика: " + ex.Message);
                await botClient.ReopenForumTopic(
                    Config.ForumId,
                    newTopic.MessageThreadId
                );
            }
        }
        finally
        {
            dialogSemaphore.Release();
        }
    }

    private async Task ErrorDialogAsync(long chatId)
    {
        await botClient.SendMessage(
            chatId,
            "Диалог не был найден\nСоздай вопрос снова"
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
                    dialogRecord.ChatIdEmployee,
                    Config.ForumId,
                    messageId
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
                    Config.ForumId,
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
                            dialogHistoryRecord = DialogHistories.GetDialogHistories(dialogRecord);
                            db.DialogHistory.Add(dialogHistoryRecord);
                            db.SaveChanges();
                        }
                        else
                        {
                            var newDialogHistoryRecord = DialogHistories.GetDialogHistories(dialogRecord);
                            if (dialogHistoryRecord != newDialogHistoryRecord)
                            {
                                dialogHistoryRecord.ListFIOSupervisor =
                                    string.Join(";", dialogRecord.ListFIOSupervisor);
                                dialogHistoryRecord.ListStartDialog = string.Join(";", dialogRecord.ListStartDialog);
                                dialogHistoryRecord.ListEndDialog = string.Join(";", dialogRecord.ListEndDialog);
                                db.DialogHistory.Update(dialogHistoryRecord);
                                db.SaveChanges();
                            }
                        }
                    }

                DialogChats.Remove(dialogRecord);
                await botClient.SendMessage(
                    Config.ForumId,
                    messageThreadId: dialogRecord.MessageThreadId,
                    text: "<b>🔥 Диалог завершен</b>\n\n" + (dialogRecord.ListStartDialog.Count == 0 ? "Диалог удалится через 5 сек" : ""),
                    parseMode: ParseMode.Html
                );

                UsersList.First(x => x.ChatId == dialogRecord.ChatIdEmployee).CurrentMode =
                    Substitution.ModeCode["signed"];
                await botClient.SendMessage(
                    dialogRecord.ChatIdEmployee,
                    "<b>🔥 Диалог завершен</b>\n\n" + (dialogRecord.ListStartDialog.Count == 0 ? "Диалог удалится через 5 сек" : ""),
                    replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["signed"]),
                    parseMode: ParseMode.Html
                );

                if (dialogRecord.ListStartDialog.Count != 0)
                {
                    await botClient.SendMessage(
                        dialogRecord.ChatIdEmployee,
                        "<b>⭐ Оценка диалога</b>\n\nОцени, помогли ли тебе решить вопрос",
                        replyMarkup: Keyboards.DialogQuality(dialogRecord.Token),
                        parseMode: ParseMode.Html
                    );
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(5000);
                        await botClient.CloseForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId
                        );

                        await botClient.EditForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId,
                            dialogRecord.Token,
                            Substitution.EmojiKeys["end"]
                        );
                    });
                }
                else
                {
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(5000);
                        await botClient.DeleteForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId
                        );
                    });
                }
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
                            dialogHistoryRecord = DialogHistories.GetDialogHistories(dialogRecord);
                            db.DialogHistory.Add(dialogHistoryRecord);
                            db.SaveChanges();
                        }
                        else
                        {
                            var newDialogHistoryRecord = DialogHistories.GetDialogHistories(dialogRecord);
                            if (dialogHistoryRecord != newDialogHistoryRecord)
                            {
                                dialogRecord.ListEndDialog.Add(Substitution.GetCorrectDateTime);
                                dialogHistoryRecord.ListFIOSupervisor =
                                    string.Join(";", dialogRecord.ListFIOSupervisor);
                                dialogHistoryRecord.ListStartDialog = string.Join(";", dialogRecord.ListStartDialog);
                                dialogHistoryRecord.ListEndDialog = string.Join(";", dialogRecord.ListEndDialog);
                                db.DialogHistory.Update(dialogHistoryRecord);
                                db.SaveChanges();
                            }
                        }
                    }

                DialogChats.Remove(dialogRecord);
                await botClient.SendMessage(
                    Config.ForumId,
                    messageThreadId: dialogRecord.MessageThreadId,
                    text: "<b>🔥 Диалог завершен</b>\n\n" + (dialogRecord.ListStartDialog.Count == 0 ? "Диалог удалится через 5 сек" : ""),
                    parseMode: ParseMode.Html
                );

                UsersList.First(x => x.ChatId == dialogRecord.ChatIdEmployee).CurrentMode =
                    Substitution.ModeCode["signed"];
                await botClient.SendMessage(
                    dialogRecord.ChatIdEmployee,
                    "<b>🔥 Диалог завершен</b>\n\n" + (dialogRecord.ListStartDialog.Count == 0 ? "Диалог удалится через 5 сек" : ""),
                    replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["signed"]),
                    parseMode: ParseMode.Html
                );

                if (dialogRecord.ListStartDialog.Count != 0)
                {
                    await botClient.SendMessage(
                        dialogRecord.ChatIdEmployee,
                        "<b>⭐ Оценка диалога</b>\n\nОцени, помогли ли тебе решить вопрос",
                        replyMarkup: Keyboards.DialogQuality(dialogRecord.Token),
                        parseMode: ParseMode.Html
                    );
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(5000);
                        await botClient.CloseForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId
                        );

                        await botClient.EditForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId,
                            dialogRecord.Token,
                            Substitution.EmojiKeys["end"]
                        );
                    });
                }
                else
                {
                    _ = Task.Run(async () =>
                    {
                        await Task.Delay(5000);
                        await botClient.DeleteForumTopic(
                            Config.ForumId,
                            dialogRecord.MessageThreadId
                        );
                    });
                }
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