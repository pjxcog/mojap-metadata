import pandas as pd
import pytest
# from mojap_metadata.converters.postgres_converter import PostgresConverter
from mojap_metadata.converters.database_converter import DatabaseConverter, database_functions as df

from pathlib import Path
import sqlalchemy as sa
from sqlalchemy import text as sqlAlcText, DDL, event
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.types import Integer, Float, String, DateTime, Date, Boolean, VARCHAR, TIMESTAMP, Numeric, DECIMAL


""" Logging... comment out to switch off 
    https://docs.sqlalchemy.org/en/20/core/engines.html#configuring-logging
    $ pytest tests/test_database_converter_postgres.py --log-cli-level=INFO

    SQLalchemy.inspect() function returns Inspector object. see documentation... 
    https://docs.sqlalchemy.org/en/20/core/reflection.html#sqlalchemy.engine.reflection.Inspector
"""
import logging

logging.basicConfig(filename='db.log')
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

TEST_ROOT = Path(__file__).resolve().parent
testSchemaName = 'schema001'
testDatabaseName = 'testpg0'


def _create_schema(engine: sa.engine.Engine, schemaName: str):
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(CreateSchema(name=schemaName, if_not_exists=True))


def _check_test_setup(engine: sa.engine.Engine):
    insp = sa.inspect(engine)
    hasTable = insp.has_table(testDatabaseName, schema=testSchemaName)
    listSchema = insp.get_schema_names() 
    hasSchema = testSchemaName in listSchema
    logging.info(listSchema)

    logging.info(f'has table?: {hasTable}, has schema?: {hasSchema}')
    logging.info(insp.get_table_names(testSchemaName))

    return hasSchema, hasTable


def _read_in_files(engine: sa.engine.Engine, files: list):
    logging.info('read_in_files...')
    for file in files:
        # Read file
        tabledf = pd.read_csv(str(file), index_col=None)

        # Create table
        filename = str(file).rsplit("/")[-1].replace(".csv", "")
        logging.info(f'..{testSchemaName}.{filename}')

        # Define datatype
        dtypedict = {
            "my_int": Integer,
            "my_float": Float,
            "my_decimal": Float,
            "my_bool": Boolean,
            "my_website": String,
            "my_email": String,
            "my_datetime": DateTime,
            "my_date": Date,
            "my_primary_key": Integer,
        }

        res = tabledf.to_sql(
            filename,
            engine,
            schema=testSchemaName,
            if_exists="replace",
            index=False,
            dtype=dtypedict,
        )
        logging.info(f'rows affected...{str(res)}')

        # Sample comment for column for testing
        qryDesc = sqlAlcText(f"COMMENT ON COLUMN {testSchemaName}.{filename}.my_int IS 'This is the int column';")
        
        # Sample NULLABLE column for testing
        qryNullable = sqlAlcText(f"ALTER TABLE {testSchemaName}.{filename} ALTER COLUMN my_primary_key SET NOT NULL;")

        # Sample PrimaryKey column for testing
        qryPk = sqlAlcText(f"ALTER TABLE {testSchemaName}.{filename} ADD CONSTRAINT my_pk PRIMARY KEY (my_primary_key);")

        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            res1 = connection.execute(qryDesc)
            res2 = connection.execute(qryNullable)
            # res3 = connection.execute(qryPk)
            # connection.commit()
        

def load_data(postgres_connection):
    """ For loading the data and updating the table with the constraints and metadata
        https://docs.sqlalchemy.org/en/14/core/connections.html#sqlalchemy.engine.Connection.execute
    """    
    
    path = TEST_ROOT / "data/sqlalchemy_converter"
    files = sorted(Path.glob(path, "testpg*.csv"))
    engine = postgres_connection[0]

    hasSchema, hasTable = _check_test_setup(engine)

    if not hasSchema:    
        logging.info('Create schema')
        _create_schema(engine, testSchemaName)
    else:
        logging.info("Schema already exist.")

    if not hasTable:
        logging.info('Create tables')
        _read_in_files(engine, files)
    else:
        logging.info("Tables already exist.")


def test_connection(postgres_connection):
    pgsql = postgres_connection[1]
    engine = postgres_connection[0]
    assert engine is not None
    assert ("system is ready to accept connections") in pgsql.read_bootlog()


def test_dsn_and_url(postgres_connection):
    pgsql = postgres_connection[1]
    expected = {
        "port": 5433,
        "host": "127.0.0.1",
        "user": "postgres",
        "database": "test",
    }

    assert pgsql.dsn() == expected
    assert pgsql.url() == "postgresql://postgres@127.0.0.1:5433/test"



def test_meta_data_object_list(postgres_connection):
    engine = postgres_connection[0]

    with engine.connect() as conn:
        load_data(postgres_connection)

        hasSchema, hasTable = _check_test_setup(engine)
        
        pc = DatabaseConverter()
        output = pc.generate_from_meta(conn, testSchemaName)

        for i in output.items():
            logging.info(f'>>>{i[0]}')
            logging.info(f'>>>{len(i[1])}')
            assert len(i[1]) == 2, f'incorrect number of tables. {len(i[1])} returned. List: {i[1]}'
            assert i[0] == f"schema: {testSchemaName}", f'schema name not "{testSchemaName}" >> actual value passed = {i[0]}'


def test_meta_data_object(postgres_connection):

    expected = {
        'name': f'{testDatabaseName}',
        'columns': [
            {
                'name': 'my_int',
                'type': 'int32',
                'description': 'This is the int column',
                'nullable': True
            },
            {
                'name': 'my_float',
                'type': 'float64',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_decimal',
                'type': 'float64',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_bool',
                'type': 'bool',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_website',
                'type': 'string',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_email',
                'type': 'string',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_datetime',
                'type': 'timestamp(ms)',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_date',
                'type': 'date64',
                'description': 'None',
                'nullable': True
            },
            {
                'name': 'my_primary_key',
                'type': 'int32',
                'description': 'None',
                'nullable': False
            },
        ],
        '$schema': 'https://moj-analytical-services.github.io/metadata_schema/mojap_metadata/v1.3.0.json',
        'description': '',
        'file_format': '',
        'sensitive': False,
        'primary_key': [],
        'partitions': [],
    }
    engine = postgres_connection[0]
    load_data(postgres_connection)
    
    with engine.connect() as conn:
        pc = DatabaseConverter()
        meta_output = pc.get_object_meta(conn, testDatabaseName, testSchemaName)

        assert len(meta_output.columns) == 9, f'number of columns not 9, actual length = {len(meta_output.columns)}'
        
        assert meta_output.column_names == [
                "my_int",
                "my_float",
                "my_decimal",
                "my_bool",
                "my_website",
                "my_email",
                "my_datetime",
                "my_date",
                "my_primary_key",
            ], f'columns names miss-match >> passed {meta_output.column_names}'
        
        assert meta_output.columns[0]["description"] == "This is the int column", f'column description missmatch, expecting "This is the int column" >> {meta_output.columns[0]}'
        
        assert expected == meta_output.to_dict(), f'expected dictionary not received, actual >> {meta_output.to_dict()}'
        



# def test_get_primarykey(postgres_connection):
#     """  """
#     load_data(postgres_connection)
#     engine = postgres_connection[0]
#     pk = df.get_constraint_pk(engine, testDatabaseName, "schema001")
#     logging.info(pk)
#     assert 'my_pk' == pk['name']
#     assert ['my_primary_key','my_int'] == pk['constrained_columns'], f'Primary key as "my_primary_key, my_int" not identified, returning: {pk["constrained_columns"]}'





""" 
    This test is not dialect specific, it confirms the mojap meta type convertion.
    It could probably go in a seperate test file...
"""
@pytest.mark.parametrize(
    "inputtype,expected",
    [
        (Integer(), "int32"),
        (Float(precision=10, decimal_return_scale=2), "float64"),
        (String(), "string"),
        (String(length=4000), "string"),
        (VARCHAR(length=255), "string"),
        (Date(), "date64"),
        (Boolean(), "bool"),
        (DateTime(), "datetime"),
        (TIMESTAMP(timezone=False), "timestamp(ms)"),
        (Numeric(precision=15, scale=2), "float64"),
        (DECIMAL(precision=8), "decimal")
    ],
)
def test_convert_to_mojap_type(inputtype: type, expected: str):
    pc = DatabaseConverter()
    actual = pc.convert_to_mojap_type(str(inputtype))
    assert actual == expected
