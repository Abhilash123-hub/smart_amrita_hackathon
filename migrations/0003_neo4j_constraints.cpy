// Migration 0003: Neo4j Constraints for W3C PROV-O Lineage Graph

CREATE CONSTRAINT entity_asset_hash_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.asset_hash IS UNIQUE;

CREATE CONSTRAINT activity_id_unique IF NOT EXISTS
FOR (a:Activity) REQUIRE a.activity_id IS UNIQUE;

CREATE CONSTRAINT agent_id_unique IF NOT EXISTS
FOR (ag:Agent) REQUIRE ag.agent_id IS UNIQUE;

CREATE INDEX entity_domain_idx IF NOT EXISTS
FOR (e:Entity) REQUIRE e.source_domain;
