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
#elif НТП
  public string Division { get; set; } = "НТП";
#else
  public string Division { get; set; } = "НЦК";
#endif

#if НЦК && !DEBUG
  public string BotToken { get; } = "6004209126:AAGayH0rZhI7iCNO8_qBDIw89rmSFnqAmF8";
  public long ForumId = -1002199294331;
  public string TopicUrl = "https://t.me/c/2199294331";
#elif НТП && !DEBUG
  public string BotToken { get; } = "7049355164:AAHDxVmWYla6abK3azWETUG1gvGQjZt113s";
  public long ForumId = -1002472709997;
  public string TopicUrl = "https://t.me/c/2472709997";
#else
  public string BotToken { get; } = "6192641034:AAHn4fFQbILklFe_NdNNL8aFRb_KLZkOtm0";
  public long ForumId = -1002198890839;
  public string TopicUrl = "https://t.me/c/2198890839";
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
