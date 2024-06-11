using static QuestionBot.Data.Substitution;

namespace QuestionBot.Async;

public class SecurityAsync
{
  public static async void CheckNewDay()
  {
    await DelayToTime(new TimeOnly(5, 0, 0));
  }
}
