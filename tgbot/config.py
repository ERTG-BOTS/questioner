from dataclasses import dataclass
from typing import Optional

from environs import Env
from sqlalchemy import URL


@dataclass
class TgBot:
    """
    Создает объект TgBot из переменных окружения.

    Attributes
    ----------
    token : str
        Токен бота.
    use_redis : str
        Нужно ли использовать Redis.
    """

    token: str
    use_redis: bool

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект TgBot из переменных окружения.
        """
        token = env.str("BOT_TOKEN")

        use_redis = env.bool("USE_REDIS")

        return TgBot(
            token=token,
            use_redis=use_redis,
        )


@dataclass
class ForumsConfig:
    """
    Класс конфигурации ForumsConfig.

    Attributes
    ----------
    ntp_main_forum_id : str
        Идентификатор форума ТГ НТП
    ntp_trainee_forum_id : str
        Идентификатор форума ТГ НТП ОР
    nck_main_forum_id : str
        Идентификатор форума ТГ НЦК
    nck_trainee_forum_id : str
        Идентификатор форума ТГ НЦК ОР
    """

    ntp_main_forum_id: str
    ntp_trainee_forum_id: str
    nck_main_forum_id: str
    nck_trainee_forum_id: str

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект ForumsConfig из переменных окружения.
        """
        ntp_main_forum_id = env.str("NTP_MAIN_FORUM_ID")
        ntp_trainee_forum_id = env.str("NTP_TRAINEE_FORUM_ID")
        nck_main_forum_id = env.str("NCK_MAIN_FORUM_ID")
        nck_trainee_forum_id = env.str("NCK_TRAINEE_FORUM_ID")

        return ForumsConfig(
            ntp_main_forum_id=ntp_main_forum_id,
            ntp_trainee_forum_id=ntp_trainee_forum_id,
            nck_main_forum_id=nck_main_forum_id,
            nck_trainee_forum_id=nck_trainee_forum_id,
        )


@dataclass
class GoogleSheetsConfig:
    """
    Класс конфигурации GoogleSheets.

    Attributes
    ----------
    ntp_trainee_spreadsheet_id : str
        Идентификатор таблицы НТП
    ntp_trainee_sheet_name : str
        Название листа в таблице НТП
    nck_trainee_spreadsheet_id : str
        Идентификатор таблицы НЦК
    nck_trainee_sheet_name : str
        Название листа в таблице НЦК
    """

    ntp_trainee_spreadsheet_id: str
    ntp_trainee_sheet_name: str

    nck_trainee_spreadsheet_id: str
    nck_trainee_sheet_name: str

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект GoogleSheets из переменных окружения.
        """
        ntp_trainee_spreadsheet_id = env.str("NTP_TRAINEE_SPREADSHEET_ID")
        ntp_trainee_sheet_name = env.str("NTP_TRAINEE_SHEET_NAME")
        nck_trainee_spreadsheet_id = env.str("NCK_TRAINEE_SPREADSHEET_ID")
        nck_trainee_sheet_name = env.str("NCK_TRAINEE_SHEET_NAME")

        return GoogleSheetsConfig(
            ntp_trainee_spreadsheet_id=ntp_trainee_spreadsheet_id,
            ntp_trainee_sheet_name=ntp_trainee_sheet_name,
            nck_trainee_spreadsheet_id=nck_trainee_spreadsheet_id,
            nck_trainee_sheet_name=nck_trainee_sheet_name,
        )


@dataclass
class QuestionerConfig:
    """
    Класс конфигурации QuestionerConfig.

    Attributes
    ----------
    ask_clever_link : str
        Запрашивать ли регламент
    ntp_trainee_sheet_name : str
        Название листа в таблице НТП
    nck_trainee_spreadsheet_id : str
        Идентификатор таблицы НЦК
    nck_trainee_sheet_name : str
        Название листа в таблице НЦК
    """

    ask_clever_link: bool

    remove_old_questions: bool
    remove_old_questions_days: int

    activity_status: bool
    activity_warn_minutes: int
    activity_close_minutes: int

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект QuestionerConfig из переменных окружения.
        """
        ask_clever_link = env.bool("ASK_CLEVER_LINK")

        remove_old_questions = env.bool("REMOVE_OLD_QUESTIONS")
        remove_old_questions_days = env.int("REMOVE_OLD_QUESTIONS_DAYS")

        activity_status = env.bool("ACTIVITY_STATUS")
        activity_warn_minutes = env.int("ACTIVITY_WARN_MINUTES")
        activity_close_minutes = env.int("ACTIVITY_CLOSE_MINUTES")

        return QuestionerConfig(
            ask_clever_link=ask_clever_link,
            remove_old_questions=remove_old_questions,
            remove_old_questions_days=remove_old_questions_days,
            activity_status=activity_status,
            activity_warn_minutes=activity_warn_minutes,
            activity_close_minutes=activity_close_minutes,
        )


@dataclass
class DbConfig:
    """
    Класс конфигурации подключения к базе данных.
    Класс хранит в себе настройки базы

    Attributes
    ----------
    host : str
        Хост, на котором находится база данных
    password : str
        Пароль для авторизации в базе данных.
    user : str
        Логин для авторизации в базе данных.
    main_db : str
        Имя основной базы данных.
    questioner_db : str
        Имя базы данных вопросника.
    """

    host: str
    user: str
    password: str

    main_db: str
    questioner_db: str

    def construct_sqlalchemy_url(
        self,
        db_name=None,
        driver="aioodbc",
    ) -> URL:
        """
        Конструирует и возвращает SQLAlchemy-ссылку для подключения к базе данных
        """
        connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self.host};"
            f"DATABASE={db_name if db_name else self.questioner_db};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"MultipleActiveResultSets=yes;"
            f"MARS_Connection=yes;"
            f"Connection Timeout=30;"
            f"Command Timeout=60;"
            f"Pooling=yes;"
            f"Max Pool Size=100;"
            f"Min Pool Size=5;"
            f"TCP KeepAlive=yes;"
            f"ConnectRetryCount=3;"
            f"ConnectRetryInterval=10;"
        )
        connection_url = URL.create(
            f"mssql+{driver}", query={"odbc_connect": connection_string}
        )

        return connection_url

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект DbConfig из переменных окружения.
        """
        host = env.str("DB_HOST")
        user = env.str("DB_USER")
        password = env.str("DB_PASS")

        main_db = env.str("DB_MAIN_NAME")
        questioner_db = env.str("DB_QUESTIONER_NAME")

        return DbConfig(
            host=host,
            user=user,
            password=password,
            main_db=main_db,
            questioner_db=questioner_db,
        )


@dataclass
class RedisConfig:
    """
    Класс конфигурации Redis.

    Attributes
    ----------
    redis_pass : Optional(str)
        Пароль для авторизации в Redis.
    redis_port : Optional(int)
        Порт, на котором слушает сервер Redis.
    redis_host : Optional(str)
        Хост, где запущен сервер Redis.
    redis_db : Optional(str)
        Название базы
    """

    redis_pass: Optional[str]
    redis_port: Optional[int]
    redis_host: Optional[str]
    redis_db: Optional[str]

    def dsn(self) -> str:
        """
        Конструирует и возвращает Redis DSN (Data Source Name).
        """
        if self.redis_pass:
            return f"redis://:{self.redis_pass}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @staticmethod
    def from_env(env: Env):
        """
        Создает объект RedisConfig из переменных окружения.
        """
        redis_pass = env.str("REDIS_PASSWORD")
        redis_port = env.int("REDIS_PORT")
        redis_host = env.str("REDIS_HOST")
        redis_db_name = env.str("REDIS_DB")

        return RedisConfig(
            redis_pass=redis_pass,
            redis_port=redis_port,
            redis_host=redis_host,
            redis_db=redis_db_name,
        )


@dataclass
class Config:
    """
    Основной конфигурационный класс, интегрирующий в себя другие классы.

    Этот класс содержит все настройки, и используется для доступа к переменным окружения.

    Attributes
    ----------
    tg_bot : TgBot
        Хранит специфичные для бота настройки.
    db : Optional[DbConfig]
        Хранит специфичные для базы данных настройки (стандартно None).
    redis : Optional[RedisConfig]
        Хранит специфичные для Redis настройки (стандартно None).
    """

    tg_bot: TgBot
    gsheets: GoogleSheetsConfig
    forum: ForumsConfig
    questioner: QuestionerConfig
    db: DbConfig
    redis: Optional[RedisConfig] = None


def load_config(path: str = None) -> Config:
    """
    Эта функция принимает в качестве входных данных опциональный путь к файлу и возвращает объект Config.
    :param path: Путь к файлу env, из которого загружаются переменные конфигурации.
    Она считывает переменные окружения из файла .env, если он указан, в противном случае — из окружения процесса.
    :return: Объект Config с атрибутами, установленными в соответствии с переменными окружения.
    """

    # Создает объект Env.
    # Объект используется для чтения файла переменных окружения.
    env = Env()
    env.read_env(path)

    return Config(
        tg_bot=TgBot.from_env(env),
        gsheets=GoogleSheetsConfig.from_env(env),
        forum=ForumsConfig.from_env(env),
        questioner=QuestionerConfig.from_env(env),
        db=DbConfig.from_env(env),
        redis=RedisConfig.from_env(env),
    )
