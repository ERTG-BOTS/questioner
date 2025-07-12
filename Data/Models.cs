using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Text.RegularExpressions;
using QuestionBot.Data.QueueModels;
using Telegram.Bot;
using static QuestionBot.Program;

namespace QuestionBot.Data.Models;

[Table("RegisteredUsers")]
public class RegisteredUsersModel
{
    [Column("Id")]
    [Key]
    [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
    public int Id { get; set; } // Представляет уникальный идентификатор пользователя.

    public long ChatId { get; set; } // Представляет идентификатор чата пользователя.
    public required string Username { get; set; } // Представляет полное имя пользователя.
    public string? Division { get; set; } // Представляет подразделение пользователя в организации.
    public string? Position { get; set; } // Представляет должность пользователя в организации.

    [Required] public required string FIO { get; set; } // Представляет полное имя пользователя.

    public string? Boss { get; set; } // Представляет босса пользователя в организации.
    public string? Email { get; set; } // Представляет адрес электронной почты пользователя.
    public byte? Role { get; set; } // Представляет состояние администратора пользователя.

    /// <summary>
    ///     Создает новую модель данных для нового пользователя.
    /// </summary>
    /// <param name="fio">Полное имя пользователя.</param>
    /// <param name="chatId">Идентификатор чата пользователя.</param>
    /// <param name="division">Подразделение пользователя в организации.</param>
    /// <param name="position">Должность пользователя в организации.</param>
    /// <param name="boss">Босс пользователя в организации.</param>
    /// <param name="email">Адрес электронной почты пользователя.</param>
    /// <param name="role">Состояние администратора пользователя.</param>
    /// <returns>Новая модель данных для нового пользователя.</returns>
    /// <exception cref="ArgumentNullException">Параметр <paramref name="fio" /> равен <see langword="null" />.</exception>
    public static RegisteredUsersModel GetNewUser(
        string fio,
        long? chatId = null,
        string? username = null,
        string? division = null,
        string? position = null,
        string? boss = null,
        string? email = null,
        byte? role = null)
    {
        return new RegisteredUsersModel
        {
            FIO = fio ?? throw new ArgumentNullException(nameof(fio)),
            ChatId = chatId ?? 0,
            Username = username ?? "Не указан",
            Division = division ?? Config.Division ?? "СТП",
            Position = position ?? "Должность не указана",
            Boss = boss ?? "Руководитель не указан",
            Email = email ?? "Не указан",
            Role = role ?? 0
        };
    }

    public bool MatchFIO(string fio)
    {
        Regex regexFIO1 = new(@"^([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)$");
        Regex regexFIO2 = new(@"^([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)$");
        Regex regexFIO3 = new(@"^([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)");

        Match? fioMatch = null;
        if (regexFIO1.IsMatch(fio)) fioMatch = regexFIO1.Match(fio);
        else if (regexFIO2.IsMatch(fio)) fioMatch = regexFIO2.Match(fio);
        else if (regexFIO3.IsMatch(fio)) fioMatch = regexFIO3.Match(fio);

        Match? FIOMatch = null;
        if (regexFIO1.IsMatch(FIO)) FIOMatch = regexFIO1.Match(FIO);
        else if (regexFIO2.IsMatch(FIO)) FIOMatch = regexFIO2.Match(FIO);

        if (FIO.Contains(fio, StringComparison.OrdinalIgnoreCase)) return true;

        if (fioMatch is null
            || FIOMatch is null
            || fioMatch.Groups.Count < 3) return false;

        for (var i = 1; i < fioMatch.Groups.Count; i++)
            if (!FIOMatch.Groups[i].Value.Contains(fioMatch.Groups[i].Value, StringComparison.OrdinalIgnoreCase))
                return false;

        return true;
    }

    public bool MatchThisFIO()
    {
        Regex regexFIO =
            new(
                @"^([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)$|^([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)\s([а-яА-ЯёЁ]+)$");
        return regexFIO.Match(FIO).Success;
    }
}

public class UserModel
{
    // Идентификатор чата пользователя
    public long ChatId { get; set; }

    // username Телеграмм пользователя (если есть)
    public string? Username { get; set; }

    // Полное имя пользователя
    public required string FIO { get; set; }

    // Руководитель пользователя
    public required string Boss { get; set; }

    public string? Email { get; set; }

    // Должность пользователя
    public string? Position { get; set; }

    // Стартовое состояние пользователя
    public short DefaultMode { get; set; }

    // Текущее состояние пользователя
    public short CurrentMode { get; set; }

    public override bool Equals(object? obj)
    {
        if (obj == null || GetType() != obj.GetType())
            return false;

        var other = (UserModel)obj;

        return FIO == other.FIO &&
               DefaultMode == other.DefaultMode &&
               Email == other.Email &&
               Position == other.Position &&
               ChatId == other.ChatId &&
               Username == other.Username;
    }

    public override int GetHashCode()
    {
        return HashCode.Combine(FIO, DefaultMode, Email, Position, ChatId, Username);
    }

    public static async Task<UserModel?> GetCorrectUserAsync(bool isTopic, long chatId, string username = "")
    {
        var currentUser = UsersList.FirstOrDefault(x => x.ChatId == chatId);
        var correctUser = GetUser(chatId);
        Console.WriteLine(correctUser);
        if (correctUser == null)
        {
            if (isTopic)
                // await botClient.BanChatMemberAsync(
                //       new BanChatMemberRequest()
                //       {
                //         ChatId = Config.ForumId,
                //         userId = chatId,
                //       });

                await botClient.BanChatMember(Config.ForumId, chatId);
            else
                // await botClient.SendMessageAsync(
                //       new SendMessageRequest()
                //       {
                //         ChatId = chatId,
                //         Text = $"Этот бот работает только для {Config.Division}"
                //       });
                await botClient.SendMessage(chatId, $"Этот бот работает только для {Config.Division}");
            return null;
        }

        if (isTopic && correctUser.DefaultMode switch { 20 or 30 or 100 => false, _ => true })
        {
            // await botClient.BanChatMemberAsync(
            //       new BanChatMemberRequest()
            //       {
            //         ChatId = Config.ForumId,
            //         UserId = chatId
            //       });
            await botClient.BanChatMember(Config.ForumId, chatId);
            return null;
        }

        if (currentUser is null || !currentUser.Equals(correctUser))
        {
            var index = UsersList.IndexOf(currentUser!);
            if (index != -1)
                UsersList[index] = correctUser;
            else
                UsersList.Add(correctUser);
        }

        return UsersList.FirstOrDefault(x => x.ChatId == chatId);
    }

    /// <summary>
    ///     Получает информацию о пользователе из базы данных и определяет его текущее состояние.
    /// </summary>
    /// <param name="chatId">Идентификатор чата пользователя.</param>
    /// <param name="username">username Телеграмм пользователя (необязательно).</param>
    /// <returns>Объект UserModel, представляющий информацию о пользователе.</returns>
    public static UserModel? GetUser(long chatId, string username = "")
    {
        RegisteredUsersModel? user = null;
        using (AppDbContext db = new())
        {
            RegisteredUsersModel? userByUsername = null;
            RegisteredUsersModel? userByChatId = null;
            try
            {
                if (username != "Скрыто/не определено" && username != "")
                    userByUsername = db.RegisteredUsers.SingleOrDefault(x =>
                        x.Username == username &&
                        (x.Role == 10 ||
                         (x.Division == Config.Division &&
                          (x.Role == 1 || x.Role == 2 || x.Role == 3 || x.Role == 8))));
                userByChatId = db.RegisteredUsers.SingleOrDefault(x =>
                    x.ChatId == chatId &&
                    (x.Role == 10 ||
                     (x.Division.Contains(Config.Division) &&
                      (x.Role == 1 || x.Role == 2 || x.Role == 3 || x.Role == 8))));
            }
            catch
            {
                Substitution.WriteLog("Error", $"Несколько пользователей c '{username}' и/или '{chatId}'");
                var userByChatIdList = db.RegisteredUsers.Where(x => x.ChatId == chatId).ToList();
                userByChatIdList.ForEach(x => x.ChatId = 0);
                if (username != "Скрыто/не определено")
                {
                    var userByUsernameList = db.RegisteredUsers.Where(x => x.Username == username).ToList();
                    userByUsernameList.ForEach(x => x.Username = "Не указан");
                }

                db.SaveChanges();
            }

            if ((username == "Скрыто/не определено" && userByChatId != null) || userByUsername == userByChatId)
            {
                user = userByChatId;
            }
            else if (userByUsername == null && userByChatId != null)
            {
                if (username != "")
                {
                    userByChatId.Username = username;
                    db.Update(userByChatId);
                    db.SaveChanges();
                }

                user = userByChatId;
            }
            else if (userByChatId == null && userByUsername != null)
            {
                userByUsername.ChatId = chatId;
                db.Update(userByUsername);
                db.SaveChanges();
                user = userByUsername;
            }
        }

        if (user == null) return null;

        // Получаем должность пользователя
        var position = user?.Position;

        var mode = Substitution.ModeCode[user?.Role switch
        {
            1 => "signed",
            2 => "supervisor",
            3 => "signed supervisor",
            8 or 10 => "signed root",
            _ => "default"
        }];

        // Определяем текущее состояние пользователя на основе его административных прав и должности
        return new UserModel
        {
            ChatId = chatId,
            Username = user?.Username,
            FIO = user?.FIO ?? user?.Username ?? throw new Exception("FIO is null"),
            Email = user?.Email,
            Boss = user?.Boss,
            Position = position,
            DefaultMode = mode,
            CurrentMode = mode
        };
    }

    public bool ModeCodeKey(string partialKey)
    {
        foreach (var keyValuePair in Substitution.ModeCode)
            if (keyValuePair.Value == CurrentMode)
            {
                var modeCodeKey = keyValuePair.Key.ToLower();
                return modeCodeKey.Contains(partialKey.ToLower());
            }

        return false; // Не найден ключ
    }
}

[Table("DialogHistories")]
public class DialogHistories
{
    [Key] public required string Token { get; set; }

    public required string FIOEmployee { get; set; }
    public required string ListFIOSupervisor { get; set; }
    public required string StartQuestion { get; set; }
    public required int FirstMessageId { get; set; }
    public required int MessageThreadId { get; set; }
    public required string ListStartDialog { get; set; }
    public required string ListEndDialog { get; set; }
    public bool? DialogQuality { get; set; }
    public bool? DialogQualityRg { get; set; }

    public static DialogHistories GetDialogHistories(DialogChatRecord dialogRecord)
    {
        return new DialogHistories
        {
            Token = dialogRecord.Token,
            FIOEmployee = dialogRecord.FIOEmployee,
            ListFIOSupervisor = string.Join(";", dialogRecord.ListFIOSupervisor),
            StartQuestion = dialogRecord.StartQuestion,
            FirstMessageId = dialogRecord.FirstMessageId,
            MessageThreadId = dialogRecord.MessageThreadId,
            ListStartDialog = string.Join(";", dialogRecord.ListStartDialog),
            ListEndDialog = string.Join(";", dialogRecord.ListEndDialog)
        };
    }
}

/// <summary>Модель базы данных сотрудников</summary>
[Table("OldDialogHistories")]
public class OldDialogHistoryModels
{
    [Key]
    /// <summary>Идентификатор диалога</summary>
    public required string TokenDialog { get; set; }

    /// <summary>ФИО сотрудника</summary>
    public required string FIOEmployee { get; set; }

    /// <summary>ФИО РГ</summary>
    [Column("FIORG")]
    public required string FIOSupervisor { get; set; }

    /// <summary>Время начала диалога</summary>
    public DateTime TimeDialogStart { get; set; }

    /// <summary>Время окончания диалога</summary>
    public DateTime TimeDialogEnd { get; set; }

    /// <summary>Оценка диалога</summary>
    public bool? DialogQuality { get; set; }

    /// <summary>История диалога</summary>
    public required string DialogHistory { get; set; }
}