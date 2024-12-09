"""Module for loading graph data into Neo4j database, based on https://github.com/microsoft/graphrag/commit/cb0aae7e6bf1763ca5a7540d2220c11162863915"""
import pandas as pd
from neo4j import GraphDatabase

INDEXING_FOLDER = "graph_agents_indexing/output"


def batched_import(driver: GraphDatabase.driver, statement: str, df: pd.DataFrame, batch_size: int=1000) -> None:
    """
    Import a dataframe into Neo4j using a batched approach.

    Parameters:
        statement (str): Cypher query to execute for each row in the dataframe.
        df (pd.DataFrame): Dataframe to import.
        batch_size (int): Number of rows to import in each batch.
    """
    total = len(df)
    for start in range(0, total, batch_size):
        batch = df.iloc[start : min(start + batch_size, total)]
        driver.execute_query(
            "UNWIND $rows AS value " + statement,
            rows=batch.to_dict("records"),
            database_="neo4j",
        )

def create_constraints(driver: GraphDatabase.driver) -> None:
    """
    Create constraints in the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    statements = """
    create constraint chunk_id if not exists for (c:__Chunk__) require c.id is unique;
    create constraint document_id if not exists for (d:__Document__) require d.id is unique;
    create constraint entity_id if not exists for (c:__Community__) require c.community is unique;
    create constraint entity_id if not exists for (e:__Entity__) require e.id is unique;
    create constraint entity_title if not exists for (e:__Entity__) require e.name is unique;
    create constraint entity_title if not exists for (e:__Covariate__) require e.title is unique;
    create constraint related_id if not exists for ()-[rel:RELATED]->() require rel.id is unique;
    """.split(";")

    for statement in statements:
        if len((statement or "").strip()) > 0:
            driver.execute_query(statement)


def load_documents(driver: GraphDatabase.driver) -> None:
    """
    Import documents into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    doc_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_documents.parquet", columns=["id", "title"]
    )

    statement = """
    MERGE (d:__Document__ {id:value.id})
    SET d += value {.title}
    """

    batched_import(driver, statement, doc_df)

def load_text_units(driver: GraphDatabase.driver) -> None:
    """
    Import text units into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    text_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_text_units.parquet",
        columns=["id", "text", "n_tokens", "document_ids"],
    )

    statement = """
    MERGE (c:__Chunk__ {id:value.id})
    SET c += value {.text, .n_tokens}
    WITH c, value
    UNWIND value.document_ids AS document
    MATCH (d:__Document__ {id:document})
    MERGE (c)-[:PART_OF]->(d)
    """

    batched_import(driver, statement, text_df)

def load_nodes(driver: GraphDatabase.driver) -> None:
    """
    Import nodes into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    entity_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_entities.parquet",
        columns=[
            "title",
            "type",
            "description",
            "human_readable_id",
            "id",
            "text_unit_ids",
        ],
    )

    entity_embeddings_mapping = pd.read_parquet(f"{INDEXING_FOLDER}/embeddings.entity.description.parquet")
    entity_df = pd.merge(entity_df, entity_embeddings_mapping, on="id", how="left")

    entity_statement = """
    MERGE (e:__Entity__ {id:value.id})
    SET e += value {.human_readable_id, .description, title:replace(value.title,'"','')}
    WITH e, value
    CALL db.create.setNodeVectorProperty(e, "embedding", value.embedding)
    CALL apoc.create.addLabels(e, case when coalesce(value.type,"") = "" then [] else [apoc.text.upperCamelCase(replace(value.type,'"',''))] end) yield node
    UNWIND value.text_unit_ids AS text_unit
    MATCH (c:__Chunk__ {id:text_unit})
    MERGE (c)-[:HAS_ENTITY]->(e)
    """

    batched_import(driver, entity_statement, entity_df)

def load_relationships(driver: GraphDatabase.driver) -> None:
    """
    Import relationships into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    rel_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_relationships.parquet",
        columns=[
            "source",
            "target",
            "id",
            "combined_degree",
            "weight",
            "human_readable_id",
            "description",
            "text_unit_ids",
        ],
    )

    rel_statement = """
        MATCH (source:__Entity__ {name:replace(value.source,'"','')})
        MATCH (target:__Entity__ {name:replace(value.target,'"','')})
        // not necessary to merge on id as there is only one relationship per pair
        MERGE (source)-[rel:RELATED {id: value.id}]->(target)
        SET rel += value {.combined_degree, .weight, .human_readable_id, .description, .text_unit_ids}
        RETURN count(*) as createdRels
    """

    batched_import(driver, rel_statement, rel_df)

def load_communities(driver: GraphDatabase.driver) -> None:
    """
    Import communities into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    community_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_communities.parquet",
        columns=["id", "level", "title", "text_unit_ids", "relationship_ids"],
    )

    statement = """
    MERGE (c:__Community__ {community:value.id})
    SET c += value {.level, .title}
    /*
    UNWIND value.text_unit_ids as text_unit_id
    MATCH (t:__Chunk__ {id:text_unit_id})
    MERGE (c)-[:HAS_CHUNK]->(t)
    WITH distinct c, value
    */
    WITH *
    UNWIND value.relationship_ids as rel_id
    MATCH (start:__Entity__)-[:RELATED {id:rel_id}]->(end:__Entity__)
    MERGE (start)-[:IN_COMMUNITY]->(c)
    MERGE (end)-[:IN_COMMUNITY]->(c)
    RETURn count(distinct c) as createdCommunities
    """

    batched_import(driver, statement, community_df)

def load_community_reports(driver: GraphDatabase.driver) -> None:
    """
    Import community reports into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    community_report_df = pd.read_parquet(
        f"{INDEXING_FOLDER}/create_final_community_reports.parquet",
        columns=[
            "id",
            "community",
            "level",
            "title",
            "summary",
            "findings",
            "rank",
            "rank_explanation",
            "full_content",
        ],
    )

    community_statement = """
    MERGE (c:__Community__ {community:value.community})
    SET c += value {.level, .title, .rank, .rank_explanation, .full_content, .summary}
    WITH c, value
    UNWIND range(0, size(value.findings)-1) AS finding_idx
    WITH c, value, finding_idx, value.findings[finding_idx] as finding
    MERGE (c)-[:HAS_FINDING]->(f:Finding {id:finding_idx})
    SET f += finding
    """
    batched_import(driver, community_statement, community_report_df)

def load(driver: GraphDatabase.driver) -> None:
    """
    Load all data into the Neo4j database.

    Parameters:
        driver (GraphDatabase.driver): Neo4j driver.
    """
    create_constraints(driver)
    load_documents(driver)
    load_text_units(driver)
    load_nodes(driver)
    load_relationships(driver)
    load_communities(driver)
    load_community_reports(driver)
    print("Data loaded successfully.")
