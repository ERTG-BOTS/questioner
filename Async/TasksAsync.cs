using QuestionBot.Data;
using QuestionBot.Data.Models;
using Telegram.Bot;
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
    
    public static async Task RemoveOldTopics()
    {
        while (true)
        {
            await Substitution.DelayToTime(new TimeOnly(3, 30, 0));

            var oldTopics = DialogHistories.GetOldDialogHistories();
            var topicsLength = oldTopics.Length;
            Substitution.WriteLog("Топики", $"Найдено старых топиков: {topicsLength}");
            await BotAsync.DeleteOldTopics(oldTopics); // Удаление топиков из бота
            DialogHistories.RemoveOldDialogHistories(oldTopics); // Удаление топиков из базы данных
        }
    }

    public static async Task MergeDialogTask()
    {
        var questionQueueKeys = QueueManager.QuestionQueue.Keys.ToList();
        var dialogCount = QueueManager.DialogChats.Count();

        if (questionQueueKeys.Any() && (dialogCount < Config.DialogMaxCount || Config.DialogMaxCount == 0))
        {
            var minQuestionId = questionQueueKeys.Min();
            var questionRecord = QueueManager.QuestionQueue[minQuestionId];

            await QueueManager.RemoveFromQuestionQueueAsync(questionRecord.ChatId);

            UsersList.First(x => x.ChatId == questionRecord.ChatId).CurrentMode = Substitution.ModeCode["in dialog"];
            await botClient.SendMessage(
                questionRecord.ChatId,
                "<b>✅ Успешно</b>\n\nВопрос передан на рассмотрение, в скором времени тебе ответят",
                replyMarkup: Keyboards.GetCurrentKeyboard(Substitution.ModeCode["in dialog"]),
                parseMode: ParseMode.Html
            );

            await QueueManager.AddDialogAsync(questionRecord);
        }
    }

    public static async Task ExpirationOverwatchTask()
    {
        var utcNow = DateTime.UtcNow;
        foreach (var dialog in QueueManager.DialogChats.Where(x =>
                     x.LastMessageReceived != null &&
                     utcNow.Subtract((DateTime)x.LastMessageReceived).TotalMinutes > 2))
            if (utcNow.Subtract((DateTime)dialog.LastMessageReceived!).TotalMinutes > 3)
            {
                await botClient.SendMessage(
                    dialog.ChatIdEmployee,
                    "<b>🔒 Отсутствие активности | Закрытие</b>\n\nЧат был неактивен в течение 3 минут и сейчас будет закрыт",
                    parseMode: ParseMode.Html
                );

                await botClient.SendMessage(
                    Config.ForumId,
                    messageThreadId: dialog.MessageThreadId,
                    text: "<b>🔒 Отсутствие активности | Закрытие</b>\n\nЧат был неактивен в течение 3 минут и сейчас будет закрыт",
                    parseMode: ParseMode.Html
                );

                await QueueManager.EndDialogAsync(dialog);
            }
            else
            {
                await botClient.SendMessage(
                    dialog.ChatIdEmployee,
                    "<b>🚩 Отсутствие активности | Предупреждение</b>\n\nЧат был неактивен в течение 2 минут. Он закроется через минуту если не будет активности" +
                    "\nЕсли вопрос неактуален, закройте диалог",
                    parseMode: ParseMode.Html
                );

                await botClient.SendMessage(
                    Config.ForumId,
                    messageThreadId: dialog.MessageThreadId,
                    text:
                    "<b>🚩 Отсутствие активности | Предупреждение</b>\n\nЧат был неактивен в течение 2 минут. Он закроется через минуту если не будет активности" +
                    "\nЕсли вопрос неактуален, закройте диалог",
                    parseMode: ParseMode.Html
                );
            }
    }
}