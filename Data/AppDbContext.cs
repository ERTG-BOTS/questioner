using QuestionBot.Data.Models;
using Microsoft.EntityFrameworkCore;

namespace QuestionBot.Data;

public class AppDbContext : DbContext
{
  public DbSet<RegisteredUsersModel> RegisteredUsers { get; set; }
  public DbSet<OldDialogHistoryModels> OldDialogHistory { get; set; }
  public DbSet<DialogHistories> DialogHistory { get; set; }
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
      OldDialogHistory.Any();
      try
      {
        DialogHistory.Any();
      }
      catch
      {
        Database.ExecuteSqlRaw(@"
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='DialogHistories' AND xtype='U')
                    BEGIN
                        CREATE TABLE DialogHistories (
                            Token NVARCHAR(255) NOT NULL PRIMARY KEY,
                            FIOEmployee NVARCHAR(MAX) NOT NULL,
                            ListFIOSupervisor NVARCHAR(MAX) NOT NULL,
                            StartQuestion NVARCHAR(MAX) NOT NULL,
                            FirstMessageId INT NOT NULL,
                            MessageThreadId INT NOT NULL,
                            ListStartDialog NVARCHAR(MAX) NOT NULL,
                            ListEndDialog NVARCHAR(MAX) NOT NULL,
                            DialogQuality bit
                        );
                    END");
      }
      return true;
    }
    catch (Exception ex)
    {
      Substitution.WriteLog("Error", $"Ошибка подключения к базе данных. {ex.Message}");
      return false;
    }
  }
}

