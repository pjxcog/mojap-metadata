import sqlalchemy
from sqlalchemy import inspect

"""
    see https://docs.sqlalchemy.org/en/20/core/reflection.html#fine-grained-reflection-with-inspector
    
    TODO. check behaviour is consistent for all dialects. Current tests are for postgres
    (For different dialects; database and schema mean different/same thing).
    Assuming: Instance > Database > Schema > Tables > Columns
    Database is declared at the point of connection.
"""

def list_schemas(connection: sqlalchemy.engine.Engine) -> list:
    """ List non-system schemas in a database.
        method: sqlalchemy.engine.reflection.Inspector.get_schema_names(**kw: Any) → List[str]
        TODO. check system_schemas, will need to contain lists for other dialect exclusions.
    """
    insp = inspect(connection)
    response = insp.get_schema_names()

    dialect = connection.dialect.name
    if dialect == 'postgres':
        system_schemas = (
            "pg_catalog".upper(),
            "information_schema".upper(),
            "pg_toast".upper(),
            "pg_temp_1".upper(),
            "pg_toast_temp_1".upper(),
        )
    elif dialect=='oracle':
        system_schemas = (
            "ADMIN",
            "ANONYMOUS",
            "APPQOSSYS",
            "AUDSYS",
            "CTXSYS",
            "DBSFWUSER",
            "DBSNMP",
            "DIP",
            "GGSYS",
            "GSMADMIN_INTERNAL",
            "GSMUSER",
            "OUTLN",
            "PUBLIC",
            "RDSADMIN",
            "REMOTE_SCHEDULER_AGENT",
            "SYS",
            "SYS$UMF",
            "SYSBACKUP",
            "SYSDG",
            "SYSKM",
            "SYSRAC",
            "SYSTEM",
            "XDB",
            "XS$NULL"
        )
    else:
        system_schemas=()
    return [r for r in response if r.upper() not in system_schemas]


def list_tables(connection: sqlalchemy.engine.Engine, schema: str = "public") -> list:
    """ List tables in a database.
        method: sqlalchemy.engine.reflection.Inspector.get_table_names(schema: Optional[str] = None, **kw: Any) → List[str]
    """
    insp = inspect(connection)
    response = insp.get_table_names(schema)
    return [r for r in response]


# def list_dbs(connection: sqlalchemy.engine.Engine):
#     """ List databases from a connection.
#         There is no sql-alchemy equivilent.
#         I can't find any evidence this is needed.
#     """
#     response = connection.execute(
#         """
#         SELECT datname
#         FROM pg_database
#         """
#     ).fetchall()
#     return [r[0] for r in response]


def list_meta_data(connection: sqlalchemy.engine.Engine, table_name: str, schema: str ) -> list:
    """ List metadata for table in the schema declared in the connection
        https://docs.sqlalchemy.org/en/20/core/reflection.html#sqlalchemy.engine.reflection.Inspector.get_columns
    """

    insp = inspect(connection)
    response = insp.get_columns(table_name, schema)

    # cols=[list(r) for r in response]
    # rows=[list(r.values()) for r in response]

    # return rows, cols
    return response


def list_primary_keys(tableSchema: list) -> list:
    """ Extract Primary Keys from schema """
    if any(d['primary_key'] == 1 for d in tableSchema):
        pk = [d for d in tableSchema if d['primary_key'] == 1 ]
    else:
        pk = []
    return pk