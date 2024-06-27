using System.Reflection;
using QuestionBot.Data;

namespace QuestionBot;

public class ConfigInfo
{
  // Параметры подключения к базе данных SQL
  public string DbServer { get; set; }

#if DEBUG
  public string Database { get; set; } = "STPMainTemp";
#else
  public string Database { get; set; } = "STPMain";
#endif

  public string DbUser { get; set; }
  public string DbPassword { get; set; }

#if НЦК
  public string Division { get; set; } = "НЦК";
#else
  public string Division { get; set; } = "НЦК";
#endif

#if НЦК && !DEBUG
  public string BotToken { get; } = "6004209126:AAGayH0rZhI7iCNO8_qBDIw89rmSFnqAmF8";
  public long ForumId = -1002199294331;
  public string TopicUrl = "https://t.me/c/2199294331";
#else
  public string BotToken { get; } = "6671363655:AAF3X2z4VTL4EPOenB6LR7BSjpwW1GeamgI";
  public long ForumId = -1002199294331;
  public string TopicUrl = "https://t.me/c/2199294331";
#endif
  public TimeSpan DelayAfterDialog = new TimeSpan(0, 0, 5);
  public long BotChatId { get; set; }
  public int DialogMaxCount { get; set; } = 0;

  public ConfigInfo()
  {
    DbServer = "185.255.135.17";
    DbUser = "sa";
    DbPassword = "yq5UM1SW9238";
  }

  public void PrintAllSettings()
  {
    foreach (PropertyInfo property in this.GetType().GetProperties())
    {
      var value = property.GetValue(this);
      if (value is Array)
      {
        Substitution.WriteLog("Config", $"{property.Name} = {string.Join(", ", (Array)value)}");
      }
      else
      {
        Substitution.WriteLog("Config", $"{property.Name} = {value}");
      }
    }
  }
}
