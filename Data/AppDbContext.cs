using QuestionBot.Data.Models;
using Microsoft.EntityFrameworkCore;

namespace QuestionBot.Data;

public class AppDbContext : DbContext
{
  public DbSet<RegisteredUsersModel> RegisteredUsers { get; set; }
  public DbSet<DialogHistoryModels> DialogHistoryModels { get; set; }
  protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
  {
    base.OnConfiguring(optionsBuilder);
    optionsBuilder.UseSqlServer(Substitution.GetConnectionString);
  }
  public bool TryConnectAllTable()
  {
    try
    {
      RegisteredUsers.Any();
      return true;
    }
    catch (Exception ex)
    {
      Substitution.WriteLog("Error", $"Ошибка подключения к базе данных. {ex.Message}");
      return false;
    }
  }
}

