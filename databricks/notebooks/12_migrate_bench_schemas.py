# Databricks notebook source
# MAGIC %md
# MAGIC # Move the perio schemas to perio_bench (spec 019)
# MAGIC
# MAGIC The layer schemas are now named for the benches: `<layer>_dental_omop_perio` became `<layer>_perio_bench`
# MAGIC (`dental_omop_nlp.schemas`). This copies what the old schemas hold into the new ones: every table (deep
# MAGIC clone, row counts checked), the landing volume's files, and each `perio_note_classifier` version with its
# MAGIC aliases. It runs first in Load results. A table, file or model version already copied is skipped, so running
# MAGIC it again adds nothing; where the old schemas never existed (a fresh target) it does nothing. Old schemas,
# MAGIC volume and model are not dropped: it prints what to remove by hand (docs/deployment.md).
# MAGIC Synthetic data only. Serverless CPU.

# COMMAND ----------

# MAGIC %pip install -q -e ../../python

# COMMAND ----------

dbutils.library.restartPython()  # noqa: F821

# COMMAND ----------

import mlflow
from dental_omop_nlp import schemas, tracking
from mlflow.tracking import MlflowClient

dbutils.widgets.text("git_commit", "")  # noqa: F821  set by the job: the commit it was deployed from
tracking.use_git_commit(dbutils)  # noqa: F821
dbutils.widgets.text("catalog", schemas.CATALOG)  # noqa: F821
dbutils.widgets.text("model_name", "perio_note_classifier")  # noqa: F821
catalog, model_name = dbutils.widgets.get("catalog"), dbutils.widgets.get("model_name")  # noqa: F821

present = {r[0] for r in spark.sql(f"SHOW SCHEMAS IN {catalog}").collect()}  # noqa: F821
old_schemas = [s for s in schemas.MOVES if s in present]
if not old_schemas:
    print("No old perio schemas here: nothing to move.")
    dbutils.notebook.exit("nothing to move")  # noqa: F821

# COMMAND ----------

# Tables: deep clone each one the new schema lacks. Views aren't copied; they are listed to recreate by hand.
existing, views = {}, []
for s in [*old_schemas, *(schemas.MOVES[o] for o in old_schemas)]:
    if s in present:
        listed = spark.catalog.listTables(f"{catalog}.{s}")  # noqa: F821
        existing[s] = {t.name for t in listed if t.tableType != "VIEW"}
        views += [f"{s}.{t.name}" for t in listed if t.tableType == "VIEW" and s in schemas.MOVES]


def rows(schema: str, table: str) -> int:
    return spark.table(f"{catalog}.{schema}.{table}").count()  # noqa: F821


copied = 0
for action, old, new, t in schemas.migration_plan(existing):
    if action == "copy":
        spark.sql(f"CREATE TABLE {catalog}.{new}.{t} DEEP CLONE {catalog}.{old}.{t}")  # noqa: F821
        if rows(new, t) != rows(old, t):
            raise RuntimeError(f"{old}.{t} -> {new}.{t}: row counts differ ({rows(old, t)} vs {rows(new, t)})")
        copied += 1
    print(f"{action}: {old}.{t} -> {new}.{t}")
print(f"tables copied: {copied}")
if views:
    print("Views not copied; recreate them in perio_bench by hand:", ", ".join(views))

# COMMAND ----------

# Landing volume files.
old_root = f"/Volumes/{catalog}/landing_{schemas.LEGACY_DOMAIN}/data"
new_root = f"/Volumes/{catalog}/landing_perio_bench/data"


def files(root: str) -> set[str]:
    out, todo = set(), [root]
    while todo:
        for f in dbutils.fs.ls(todo.pop()):  # noqa: F821
            if f.isDir():
                todo.append(f.path)
            else:
                out.add(f.path.split(root, 1)[1].lstrip("/"))
    return out


try:
    old_files = files(old_root)
except Exception as e:  # noqa: BLE001  no old volume here
    print(f"no old landing volume ({type(e).__name__}): skipping files")
    old_files = set()
todo = schemas.files_to_copy(old_files, files(new_root) if old_files else set())
for rel in todo:
    dbutils.fs.cp(f"{old_root}/{rel}", f"{new_root}/{rel}")  # noqa: F821
print(f"files copied: {len(todo)} of {len(old_files)}")

# COMMAND ----------

# Model versions and aliases. The new registered model is a bundle resource, so it exists after the deploy.
mlflow.set_registry_uri("databricks-uc")
client = MlflowClient()
old_model = f"{catalog}.gold_{schemas.LEGACY_DOMAIN}.{model_name}"
new_model = f"{catalog}.gold_perio_bench.{model_name}"
try:
    old_versions = {int(v.version): v for v in client.search_model_versions(f"name='{old_model}'")}
except Exception as e:  # noqa: BLE001  no old model here
    print(f"no old model {old_model} ({type(e).__name__}): skipping")
    old_versions = {}

if old_versions:
    new_by_source = {int(v.tags[schemas.COPIED_FROM_TAG]): int(v.version)
                     for v in client.search_model_versions(f"name='{new_model}'")
                     if schemas.COPIED_FROM_TAG in (v.tags or {})}
    for v in schemas.versions_to_copy(list(old_versions), set(new_by_source)):
        mv = client.copy_model_version(src_model_uri=f"models:/{old_model}/{v}", dst_name=new_model)
        client.set_model_version_tag(new_model, mv.version, schemas.COPIED_FROM_TAG, str(v))
        new_by_source[v] = int(mv.version)
        print(f"model: {old_model} v{v} -> {new_model} v{mv.version}")
    # Aliases follow their version, unless the new model already has that alias (a newer promotion wins).
    have = client.get_registered_model(new_model).aliases or {}
    for alias, v in (client.get_registered_model(old_model).aliases or {}).items():
        if alias not in have and int(v) in new_by_source:
            client.set_registered_model_alias(new_model, alias, new_by_source[int(v)])
            print(f"alias {alias}: {new_model} v{new_by_source[int(v)]}")

# COMMAND ----------

print("Old schemas, volume and model left in place. After checking perio_bench, retire them "
      "(docs/deployment.md, Retiring the legacy schemas):\n"
      + "\n".join(f"DROP SCHEMA {catalog}.{s} CASCADE;" for s in old_schemas))
