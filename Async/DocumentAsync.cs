using OfficeOpenXml;
using OfficeOpenXml.Style;
using QuestionBot.Data;
using QuestionBot.Data.Models;
using Telegram.Bot;
using Telegram.Bot.Types;
using iText.Kernel.Font;
using File = System.IO.File;
using static QuestionBot.Program;
using iText.Kernel.Pdf;
using iText.Layout.Element;
using Telegram.Bot.Types.ReplyMarkups;
using iText.IO.Image;
using Telegram.Bot.Requests;
using System.Diagnostics;

namespace QuestionBot.Async;

public class DocumentAsync
{

  public static async Task DialogHistoryExcel(long chatId, int month)
  {
    using (AppDbContext dbContext = new())
    {
      var dialogHistory = dbContext.DialogHistory
                                   .ToList()
                                   .Where(x => int.TryParse(x.StartQuestion.Split('.')[1], out int Month) && Month == month)
                                   .OrderBy(x => x.FirstMessageId)
                                   .ToList();
      using (var package = new ExcelPackage())
      {
        var worksheet = package.Workbook.Worksheets.Add($"Диалоги за {month} месяц");

        worksheet.Cells[1, 1].Value = "Token";
        worksheet.Cells[1, 2].Value = "Специалист";
        worksheet.Cells[1, 3].Value = "Старший";
        worksheet.Cells[1, 4].Value = "Время вопроса";
        worksheet.Cells[1, 5].Value = "Время ответа";
        worksheet.Cells[1, 6].Value = "Время завершения";
        worksheet.Cells[1, 7].Value = "Оценка от специалиста";
        worksheet.Cells[1, 8].Value = "Оценка от старшего";

        int row = 2;


        foreach (var dialog in dialogHistory)
        {
          int rowBuffer = 0;
          int rowBufferMax = 0;

          worksheet.Cells[row, 1].Value = dialog.Token;
          worksheet.Cells[row, 2].Value = dialog.FIOEmployee;
          worksheet.Cells[row, 4].Value = dialog.StartQuestion;
          worksheet.Cells[row, 7].Value = dialog.DialogQuality switch { true => "Хорошо", false => "Плохо", _ => "Нет оценки" };
          worksheet.Cells[row, 8].Value = dialog.DialogQualityRg switch { true => "Хорошо", false => "Плохо", _ => "Нет оценки" };
          foreach (var item in dialog.ListFIOSupervisor.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 3].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          rowBuffer = 0;
          foreach (var item in dialog.ListStartDialog.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 5].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          rowBuffer = 0;
          foreach (var item in dialog.ListEndDialog.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 6].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          row += rowBufferMax;
        }
        worksheet.Cells[worksheet.Dimension.Address].AutoFitColumns();

        var fileName = $"DialogHistory_{russianCulture.DateTimeFormat.GetMonthName(month)}.xlsx";
        var filePath = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialoghistory.xlsx");
        File.WriteAllBytes(filePath, package.GetAsByteArray());
        using (FileStream fileStream = new(filePath, FileMode.Open, FileAccess.Read))
        {
          InputFile inputFileFromStream = InputFile.FromStream(fileStream, fileName);
          await botClient.SendDocumentAsync(
                new SendDocumentRequest()
                {
                  ChatId = chatId,
                  Document = inputFileFromStream
                });
        }
      }
    }
  }

  public static async Task DialogHistoryExcel(long chatId)
  {
    Stopwatch sw = new Stopwatch();
    sw.Start();
    Substitution.WriteLog("debug", "start assembling excel");
    using (AppDbContext dbContext = new())
    {
      var dialogHistory = dbContext.DialogHistory.ToList()
                                   .Where(x => DateTime.ParseExact(x.StartQuestion, "dd.MM.yyyy HH:mm:ss", russianCulture).CompareTo(DateTime.UtcNow.AddMonths(-3)) > 0)
                                   .OrderBy(x => x.FirstMessageId)
                                   .ToList();
    Substitution.WriteLog("debug", $"got all dialogues: {sw.ElapsedMilliseconds} ms");
    sw.Restart();
      using (var package = new ExcelPackage())
      {
      Substitution.WriteLog("debug", $"package open: {sw.ElapsedMilliseconds} ms");
      sw.Restart();
        var worksheet = package.Workbook.Worksheets.Add($"Диалоги за 3 месяца");

        worksheet.Cells[1, 1].Value = "Token";
        worksheet.Cells[1, 2].Value = "Специалист";
        worksheet.Cells[1, 3].Value = "Старший";
        worksheet.Cells[1, 4].Value = "Время вопроса";
        worksheet.Cells[1, 5].Value = "Время ответа";
        worksheet.Cells[1, 6].Value = "Время завершения";
        worksheet.Cells[1, 7].Value = "Оценка от специалиста";
        worksheet.Cells[1, 8].Value = "Оценка от старшего";

        int row = 2;

      Substitution.WriteLog("debug", $"populating started: {sw.ElapsedMilliseconds} ms");
      sw.Restart();
        foreach (var dialog in dialogHistory)
        {
          int rowBuffer = 0;
          int rowBufferMax = 0;

          worksheet.Cells[row, 1].Value = dialog.Token;
          worksheet.Cells[row, 2].Value = dialog.FIOEmployee;
          worksheet.Cells[row, 4].Value = dialog.StartQuestion;
          worksheet.Cells[row, 7].Value = dialog.DialogQuality switch { true => "Хорошо", false => "Плохо", _ => "Нет оценки" };
          worksheet.Cells[row, 8].Value = dialog.DialogQualityRg switch { true => "Хорошо", false => "Плохо", _ => "Нет оценки" };
          foreach (var item in dialog.ListFIOSupervisor.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 3].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          rowBuffer = 0;
          foreach (var item in dialog.ListStartDialog.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 5].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          rowBuffer = 0;
          foreach (var item in dialog.ListEndDialog.Split(";"))
          {
            worksheet.Cells[row + rowBuffer++, 6].Value = item;
          }
          if (rowBufferMax < rowBuffer)
          {
            rowBufferMax = rowBuffer;
          }
          row += rowBufferMax;
        }
       Substitution.WriteLog("debug", $"populated: {sw.ElapsedMilliseconds} ms");
      sw.Restart();
        worksheet.Cells[worksheet.Dimension.Address].AutoFitColumns();
      Substitution.WriteLog("debug", $"autofitted: {sw.ElapsedMilliseconds} ms");
      sw.Restart();

        var fileName = $"DialogHistory_3m_{DateTime.UtcNow.AddHours(5): dd-MM-yy HH-mm}.xlsx";
        var filePath = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialoghistory.xlsx");
        File.WriteAllBytes(filePath, package.GetAsByteArray());
      Substitution.WriteLog("debug", $"file saved: {sw.ElapsedMilliseconds} ms");
      sw.Restart();
        using (FileStream fileStream = new(filePath, FileMode.Open, FileAccess.Read))
        {
          InputFile inputFileFromStream = InputFile.FromStream(fileStream, fileName);
          await botClient.SendDocumentAsync(
                new SendDocumentRequest()
                {
                  ChatId = chatId,
                  Document = inputFileFromStream
                });
        }
        Substitution.WriteLog("debug", $"file sent: {sw.ElapsedMilliseconds} ms");
        sw.Stop();
      }
    }
  }



  public static async Task OldDialogHistoryExcel(long chatId, int month)
  {
    using (AppDbContext dbContext = new())
    {
      var dialogHistory = dbContext.OldDialogHistory
                                   .Where(x => x.TimeDialogStart.Month == month)
                                   .OrderBy(x => x.TimeDialogStart)
                                   .ToList();

      using (var package = new ExcelPackage())
      {
        var worksheet = package.Workbook.Worksheets.Add($"Диалоги за {month} месяц");

        worksheet.Cells[1, 1].Value = "Token";
        worksheet.Cells[1, 2].Value = "Специалист";
        worksheet.Cells[1, 3].Value = "Старший";
        worksheet.Cells[1, 4].Value = "Время начала";
        worksheet.Cells[1, 5].Value = "Время окончания";
        worksheet.Cells[1, 6].Value = "Оценка";

        using (var range = worksheet.Cells[1, 1, 1, 6])
        {
          range.Style.Font.Bold = true;
          range.Style.Fill.PatternType = ExcelFillStyle.Solid;
          range.Style.Fill.BackgroundColor.SetColor(System.Drawing.Color.LightGray);
          range.Style.HorizontalAlignment = ExcelHorizontalAlignment.Center;
        }

        for (int i = 0; i < dialogHistory.Count; i++)
        {
          var record = dialogHistory[i];
          worksheet.Cells[i + 2, 1].Value = record.TokenDialog;
          worksheet.Cells[i + 2, 2].Value = record.FIOEmployee;
          worksheet.Cells[i + 2, 3].Value = record.FIOSupervisor;
          worksheet.Cells[i + 2, 4].Value = record.TimeDialogStart.AddHours(3).ToString("dd.MM.yyyy HH:mm:ss", russianCulture);
          worksheet.Cells[i + 2, 5].Value = record.TimeDialogEnd.AddHours(3).ToString("dd.MM.yyyy HH:mm:ss", russianCulture);
          worksheet.Cells[i + 2, 6].Value = record.DialogQuality.HasValue ?
                        (record.DialogQuality.Value ? "Положительная" : "Отрицательная")
                        : "Отсуствует";
        }

        worksheet.Cells[worksheet.Dimension.Address].AutoFitColumns();

        var fileName = $"DialogHistory_{russianCulture.DateTimeFormat.GetMonthName(month)}.xlsx";
        var filePath = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialoghistory.xlsx");
        File.WriteAllBytes(filePath, package.GetAsByteArray());
        using (FileStream fileStream = new(filePath, FileMode.Open, FileAccess.Read))
        {
          InputFile inputFileFromStream = InputFile.FromStream(fileStream, fileName);
          await botClient.SendDocumentAsync(
                new SendDocumentRequest()
                {
                  ChatId = chatId,
                  Document = inputFileFromStream
                });
        }
      }
    }
  }

  public static async Task DialogHistoryPDF(long chatId, OldDialogHistoryModels currentDialog)
  {
    string[] dialogHistory = currentDialog.DialogHistory.Split('@');
    if (currentDialog.FIOSupervisor == currentDialog.FIOEmployee)
    {
      var debugHistory = dialogHistory.Select(x => x.Split('#')[0]).Where(x => !string.IsNullOrEmpty(x)).Distinct().ToList();
      if (debugHistory.Count == 2 && int.TryParse(debugHistory[0], out var chatId0) && int.TryParse(debugHistory[1], out var chatId1))
      {
        using (AppDbContext db = new())
        {
          var users = db.RegisteredUsers.Where(x => x.ChatId == chatId0 || x.ChatId == chatId1);
          currentDialog.FIOEmployee = users.First(x => x.ChatId == chatId0).FIO;
          currentDialog.FIOSupervisor = users.First(x => x.ChatId == chatId1).FIO;
        }
      }
    }
    await botClient.SendMessageAsync(
      new SendMessageRequest()
      {
        ChatId = chatId,
        Text = string.Format("Найден диалог {0} с {1} в {2} - {3}",
            currentDialog.FIOSupervisor,
            currentDialog.FIOEmployee,
            currentDialog.TimeDialogStart.AddHours(3).ToString("dd.MM.yyyy HH:mm:ss", russianCulture),
            currentDialog.TimeDialogEnd.AddHours(3).ToString("HH:mm:ss", russianCulture))
      });

    string fileName = $"Диалог_{currentDialog.TokenDialog}.pdf";

    string fontPath = Path.Combine(AppContext.BaseDirectory, "Data", "TimesNewRoman.ttf");
    string filePath = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialog.pdf");
    string dialogDocument = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialogDocument");
    string messagePhotoPath = Path.Combine($"{AppContext.BaseDirectory}", "buffer", "dialogPhoto.jpg");

    using PdfWriter writer = new(filePath);

    PdfFont font = PdfFontFactory.CreateFont(fontPath, "cp1251", PdfFontFactory.EmbeddingStrategy.PREFER_EMBEDDED, true);

    PdfDocument pdf = new(writer);
    iText.Layout.Document document = new(pdf);

    long[] usersInDialog = { 0, 0 };

    using (AppDbContext db = new())
    {
      var a = db.RegisteredUsers.Where(x => x.FIO == currentDialog.FIOEmployee || x.FIO == currentDialog.FIOSupervisor).ToList();
      if (a.Count == 2)
      {
        usersInDialog[0] = a.FirstOrDefault(x => x.FIO == currentDialog.FIOEmployee)?.ChatId ?? 0;
        usersInDialog[1] = a.FirstOrDefault(x => x.FIO == currentDialog.FIOSupervisor)?.ChatId ?? 0;
      }
    }

    try
    {
      Paragraph CreateDefaultParagraph()
      {
        Paragraph paragraph = new Paragraph();
        paragraph.SetFont(font);
        paragraph.SetTextAlignment(iText.Layout.Properties.TextAlignment.LEFT);
        return paragraph;
      }
      void AddTextToDocument(string text)
      {
        Paragraph paragraph = CreateDefaultParagraph();
        paragraph.Add(text);
        paragraph.Add(Environment.NewLine);
        document.Add(paragraph);
      }
      void AddImageToDocument(Image image)
      {
        Paragraph paragraph = CreateDefaultParagraph();
        paragraph.Add(image);
        paragraph.Add(Environment.NewLine);
        document.Add(paragraph);
      }
      void AddTextToDocumentBold(string text)
      {
        Paragraph paragraph = CreateDefaultParagraph();
        paragraph.Add(text).SetBold();
        paragraph.Add(Environment.NewLine);
        document.Add(paragraph);
      }

      string start = string.Format("Диалог {0} с {1} в {2} - {3} МСК\n",
            currentDialog.FIOSupervisor,
            currentDialog.FIOEmployee,
            currentDialog.TimeDialogStart.AddHours(3).ToString("dd.MM.yyyy HH:mm:ss", russianCulture),
            currentDialog.TimeDialogEnd.AddHours(3).ToString("HH:mm:ss", russianCulture));
      AddTextToDocumentBold(start);

      int documentNumber = 1;

      foreach (string message in dialogHistory)
      {
        if (message == "") break;
        string[] messageSplit = message.Split('#');
        long currentChatId = long.Parse(messageSplit[0]);
        MessageId thisMessageId = await botClient.CopyMessageAsync(
                                        new CopyMessageRequest()
                                        {
                                          ChatId = 5405986946,
                                          FromChatId = currentChatId,
                                          MessageId = int.Parse(messageSplit[1])
                                        });
        Message thisMessage = await botClient.EditMessageReplyMarkupAsync(
                                        new EditMessageReplyMarkupRequest()
                                        {
                                          ChatId = 5405986946,
                                          MessageId = thisMessageId.Id,
                                          ReplyMarkup = new InlineKeyboardMarkup(InlineKeyboardButton.WithCallbackData("1"))
                                        });

        string sender = currentChatId == usersInDialog[0]
                        ? currentDialog.FIOEmployee
                        : currentChatId == usersInDialog[1]
                          ? currentDialog.FIOSupervisor
                          : "Отправитель не определен";

        AddTextToDocumentBold(sender);

        string? textMessage = thisMessage.Caption ?? thisMessage.Text ?? null;
        if (textMessage != null)
          AddTextToDocument(textMessage);


        if (thisMessage.Photo != null)
        {
          var messagePhoto = await botClient.GetFileAsync(
            new GetFileRequest()
            { FileId = thisMessage.Photo.Last().FileId });
          FileStream downloadPhoto = new FileStream(messagePhotoPath, FileMode.Create);
          await botClient.DownloadFileAsync(messagePhoto!.FilePath!, downloadPhoto);
          downloadPhoto.Dispose();
          ImageData imagedata = ImageDataFactory.Create(messagePhotoPath);
          Image image = new(imagedata);
          image.Scale(0.3f, 0.3f);

          AddImageToDocument(image);
        }


        if (thisMessage.Document != null)
        {
          AddTextToDocument($"Документ {documentNumber}");

          Telegram.Bot.Types.File file = await botClient.GetFileAsync(
            new GetFileRequest()
            { FileId = thisMessage.Document.FileId });
          using (FileStream fileStream = new FileStream(dialogDocument, FileMode.Create))
          {
            await botClient.DownloadFileAsync(file.FilePath!, fileStream);
          }

          using (FileStream fileStream = new FileStream(dialogDocument, FileMode.Open, FileAccess.Read))
          {
            InputFile inputFileFromStream = InputFile.FromStream(fileStream, $"Документ_{documentNumber++}_{thisMessage.Document.FileName}");
            await botClient.SendDocumentAsync(
              new SendDocumentRequest()
              {
                ChatId = chatId,
                Document = inputFileFromStream
              });
          }

          await botClient.EditMessageCaptionAsync(new EditMessageCaptionRequest()
          {
            ChatId = 5405986946,
            MessageId = thisMessageId.Id,
            Caption = "0"
          });
        }

        if (thisMessage.Sticker != null)
          AddTextToDocument("Телеграмм стикер");

        await botClient.DeleteMessageAsync(
          new DeleteMessageRequest()
          {
            ChatId = 5405986946,
            MessageId = thisMessageId.Id
          });
        await Task.Delay(500);
      }

      document.Close();
      writer.Dispose();

      using (FileStream fileStream = new(filePath, FileMode.Open, FileAccess.Read))
      {
        InputFile inputFileFromStream = InputFile.FromStream(fileStream, fileName);
        await botClient.SendDocumentAsync(
          new SendDocumentRequest()
          {
            ChatId = chatId,
            Document = inputFileFromStream
          });
      }
    }
    catch (Exception ex)
    {
      Substitution.WriteLog("Error", $"Ошибка при создании PDF: {ex.Message}\n{ex.StackTrace}");
      await botClient.SendMessageAsync(
        new SendMessageRequest()
        {
          ChatId = chatId,
          Text = "Ошибка при формировании файла диалога"
        });
      return;
    }
  }
}
