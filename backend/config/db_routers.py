REMOTE_DATABASE_ALIASES = frozenset({"scm_remote", "ads_analysis_remote"})


class ReadOnlyRemoteDatabaseRouter:
    """Keep Django models and migrations on the project-owned default database."""

    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        return None

    def allow_relation(self, obj1, obj2, **hints):
        database1 = getattr(getattr(obj1, "_state", None), "db", None)
        database2 = getattr(getattr(obj2, "_state", None), "db", None)
        if (
            database1
            and database2
            and database1 != database2
            and ({database1, database2} & REMOTE_DATABASE_ALIASES)
        ):
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db in REMOTE_DATABASE_ALIASES:
            return False
        return None
