# type: ignore

import sys
from typing import Any
# from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame

from pyspark.sql.functions import array, col, explode, lit, struct
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import SQLContext
from pyspark.ml.feature import StringIndexer
from pyspark.sql.window import Window
from pyspark.sql.functions import lag


def melt(
    df: DataFrame, id_vars: list[Any], value_vars: list[Any], var_name: str = "variable", value_name: str = "value"
) -> DataFrame:
    """Convert :class:`DataFrame` from wide to long format."""

    # Create array<struct<variable: str, value: ...>>
    _vars_and_vals = array(*(struct(lit(c).alias(var_name), col(c).alias(value_name)) for c in value_vars))

    # Add to the DataFrame and explode
    _tmp = df.withColumn("_vars_and_vals", explode(_vars_and_vals))

    cols = id_vars + [col("_vars_and_vals")[x].alias(x) for x in [var_name, value_name]]
    return _tmp.select(*cols)


# @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext()
sqlContext = SQLContext(sc)
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)
DATABASE_NAME = "sfeda-mlops-retrain-database"
S3_OUTPUT_PATH = "s3://sfeda-mlops-processed/processed_data/"
SEED = 13


# Melt dataset sales_train_evaluation_csv

datasource0 = glueContext.create_dynamic_frame.from_catalog(
    database=DATABASE_NAME, table_name="sales_train_evaluation_csv", transformation_ctx="datasource0"
)

datasource0_df = datasource0.toDF()
col_list = ["d_" + str(_i + 1) for _i in range(1941)]
id_vars = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
datasource0_df_melted = melt(df=datasource0_df, id_vars=id_vars, value_vars=col_list)

# Merge datasets ## @type: Join

calendar = glueContext.create_dynamic_frame.from_catalog(
    database=DATABASE_NAME,
    table_name="calendar_csv",
    redshift_tmp_dir=args["TempDir"],
    transformation_ctx="<transformation_ctx>",
)
calendar = calendar.toDF()
datasource0_df_melted = datasource0_df_melted.join(calendar, calendar.d == datasource0_df_melted.variable, how="left")

sell_prices = glueContext.create_dynamic_frame.from_catalog(
    database=DATABASE_NAME,
    table_name="sell_prices_csv",
    redshift_tmp_dir=args["TempDir"],
    transformation_ctx="<transformation_ctx>",
)
sell_prices = sell_prices.toDF()
sell_prices = (
    sell_prices.withColumnRenamed("store_id", "store_id_1")
    .withColumnRenamed("item_id", "item_id_1")
    .withColumnRenamed("wm_yr_wk", "wm_yr_wk_1")
)

sqlContext.registerDataFrameAsTable(datasource0_df_melted, "datasource0_df_melted")
sqlContext.registerDataFrameAsTable(sell_prices, "sell_prices")

datasource0_df_melted_merged = sqlContext.sql(
    "SELECT * FROM datasource0_df_melted"
    + "LEFT join sell_prices"
    + "ON ((datasource0_df_melted.store_id = sell_prices.store_id_1) and"
    + "(datasource0_df_melted.item_id = sell_prices.item_id_1) and"
    + "(datasource0_df_melted.wm_yr_wk = sell_prices.wm_yr_wk_1))"
)


# Fill na values
datasource0_df_melted_merged = datasource0_df_melted_merged.fillna({"sell_price": 0})


# Encoding values
def encode_categorical_columns(columns: Any, df: Any) -> Any:

    for column in columns:
        indexer = StringIndexer(inputCol=column, outputCol=column + "_encoded")
        df = indexer.fit(df).transform(df)

    return df


categorical_features = [
    "item_id",
    "dept_id",
    "cat_id",
    "store_id",
    "state_id",
    "wm_yr_wk",
    "weekday",
    "month",
    "event_name_1",
    "event_name_2",
    "snap_ca",
    "snap_tx",
    "snap_wi",
]

categorical_features_new = [x + "_encoded" for x in categorical_features]


datasource0_df_encoded = encode_categorical_columns(categorical_features, datasource0_df_melted_merged)

# Create Lag features
datasource0_df_encoded = datasource0_df_encoded.withColumn(
    "lag_1", lag("value", 1).over(Window.partitionBy("id").orderBy("date"))
)
datasource0_df_encoded = datasource0_df_encoded.withColumn(
    "lag_3", lag("value", 3).over(Window.partitionBy("id").orderBy("date"))
)
datasource0_df_encoded = datasource0_df_encoded.withColumn(
    "lag_5", lag("value", 5).over(Window.partitionBy("id").orderBy("date"))
)

# Keep only relevant columns for training

keep_columns = ["value"] + categorical_features_new + ["sell_price", "lag_1", "lag_3", "lag_5"]
datasource0_df_encoded = datasource0_df_encoded.select(*keep_columns)

# Split data on train and test

train, test = datasource0_df_encoded.randomSplit(weights=[0.8, 0.2], seed=SEED)


train_dynamic = DynamicFrame.fromDF(train, glueContext, "datasource0_dynamic_frame_melted")
test_dynamic = DynamicFrame.fromDF(test, glueContext, "datasource0_dynamic_frame_melted")


repartition_train = train_dynamic.repartition(1)
repartition_test = test_dynamic.repartition(1)


datasink_train = glueContext.write_dynamic_frame.from_options(
    frame=repartition_train,
    connection_type="s3",
    connection_options={"path": S3_OUTPUT_PATH + "train-data"},
    format_options={"writeHeader": False},
    format="csv",
    transformation_ctx="datasink_train",
)

datasink_test = glueContext.write_dynamic_frame.from_options(
    frame=repartition_test,
    connection_type="s3",
    connection_options={"path": S3_OUTPUT_PATH + "val-data"},
    format_options={"writeHeader": False},
    format="csv",
    transformation_ctx="datasink_test",
)

job.commit()
