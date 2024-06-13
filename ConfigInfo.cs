using System.Reflection;
using QuestionBot.Data;

namespace QuestionBot;

public class ConfigInfo
{
  // Параметры подключения к базе данных SQL
  public string DbServer { get; set; }

#if !DEBUG
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

#if DEBUG  
  public string BotToken { get; } = "6175066343:AAH8F3_0I-AQFTTmNGxKMDG1pXPcJcZ1JF8";
#elif НЦК
  public string BotToken { get; } = "6004209126:AAGayH0rZhI7iCNO8_qBDIw89rmSFnqAmF8";
#else
  public string BotToken { get; } = "6175066343:AAH8F3_0I-AQFTTmNGxKMDG1pXPcJcZ1JF8";
#endif
  public TimeSpan DelayAfterDialog = new TimeSpan(0, 0, 5);

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
