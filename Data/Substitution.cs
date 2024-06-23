using System.Text;
using static QuestionBot.Program;

namespace QuestionBot.Data;

/// <summary>
/// Класс работы со словарями
/// </summary>
public static class Substitution
{
  /// <summary>
  /// Словарь для определения модкода юзера
  /// </summary>
  public static readonly Dictionary<string, short> ModeCode = new()
  {
    {"blocked" , -1 },
    {"default" , 0 },
    {"signed" , 2 },
    {"signed supervisor" , 20 },
    {"question" , 3 },
    {"await answer" , 4 },
    {"in dialog" , 5 },
    {"supervisor" , 30 },
    {"signed root" , 100 },
    {"test" , 999 },
  };

  public static readonly Dictionary<string, string> EmojiKeys = new()
  {
    {"start", "5368808634392257474"},
    {"end", "5237699328843200968"},
    {"new", "5377316857231450742"},
    {"lost", "5372819184658949787"}
  };

  /// <summary>
  /// Словать параметоров с форматированием логов
  /// </summary>
  private static readonly Dictionary<string, string> ConsoleLog = new() {
    {"Error", "[\x1b[41mERROR\x1b[0m]"},
    {"Start", "[\x1b[32mSTARTUP\x1b[0m]"},
    {"Config", "[\x1b[32mCONFIG\x1b[0m]"},
    {"Диалог", "[\x1b[96mДИАЛОГ\x1b[0m]"},
    {"Сообщение", "[\x1b[93mСООБЩЕНИЕ\x1b[0m]"},
  };

  ///<summary>
  /// Ожидание до TimeOnly
  ///</summary>
  ///<param name="timeTo">Время до которого ожидатьо</param>
  public static async Task DelayToTime(TimeOnly timeTo)
  {
    var timeFromDelay = DateTime.UtcNow.AddHours(5);
    var timeToDelay = new DateTime(timeFromDelay.Year, timeFromDelay.Month, timeFromDelay.Day, timeTo.Hour, timeTo.Minute, 0);

    if (timeToDelay < timeFromDelay) timeToDelay = timeToDelay.AddDays(1);

    await Task.Delay(timeToDelay - timeFromDelay);
  }

  public static async Task SendJsonToUrl(string url, string json)
  {
    using (var httpClient = new HttpClient())
    {
      var content = new StringContent(json, Encoding.UTF8, "application/json");
      try { await httpClient.PostAsync(url, content); }
      catch (Exception e)
      {
        WriteLog("Error", $"Ошибка при отправке JSON: {e.Message}");
      }
    }
  }

  /// <summary>
  /// Выводит логи
  /// </summary>
  /// <param name="mode">Имя параметра логов</param>
  /// <param name="output">Данные для логирования</param>
  public static void WriteLog(string mode, string output) { Console.WriteLine($"{DateTime.UtcNow.AddHours(5):d.MM.yyyy | HH:mm:ss} {ConsoleLog[mode]} {output}"); }

  public static string WriteOutFormattedLog()
  {
    StringBuilder output = new();
    foreach (var kvp in ConsoleLog)
    {
      output.AppendLine($"{kvp.Key} | {kvp.Value}");
    }
    return output.ToString();
  }

  /// <summary>
  /// Формирует строку подключения из конфига
  /// </summary>
  /// <param name="Main">Параметр отвечающий за выбор базы данных</param>
  /// <returns>строку подключения к базе данных</returns>
  public static string GetConnectionString =>
    $"Server={Config.DbServer};database={Config.Database};TrustServerCertificate=true;" +
    $"user id={Config.DbUser};password={Config.DbPassword};";

  public static string ConvertDate(string inputDate)
  {
    if (string.IsNullOrEmpty(inputDate) || !inputDate.Contains(' '))
    {
      throw new ArgumentException("Некорректный формат даты");
    }

    string[] parts = inputDate.Split(' ');
    string dateString = parts[0];

    DateTime date = DateTime.ParseExact(dateString, "dd.MM.yyyy", russianCulture);
    date = date.AddDays(-1);

    string convertedDate = date.ToString("dd.MM.yyyy");

    return convertedDate;
  }

  public static string GetCorrectDateTime => DateTime.UtcNow.AddHours(5).ToString("dd.MM.yyyy HH:mm:ss");
}

public static class ListExtensions
{
  public static List<string> MaxString(this List<string> input, int maxLength = 4000)
  {
    List<string> parts = [];
    StringBuilder currentPart = new();
    int currentLength = 0;

    foreach (string line in input)
    {
      if (currentLength + line.Length > maxLength && currentPart.Length > 0)
      {
        parts.Add(currentPart.ToString());
        currentPart.Clear();
        currentLength = 0;
      }

      currentPart.AppendLine(line);
      currentLength += line.Length;
    }

    if (currentPart.Length > 0)
    {
      parts.Add(currentPart.ToString());
    }

    return parts;
  }
}

