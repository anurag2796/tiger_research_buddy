from dagster import Definitions, load_assets_from_modules, define_asset_job, RunConfig


from . import assets

all_assets = load_assets_from_modules([assets])

# Define Job Configurations
restricted_config = RunConfig(
    ops={
        "rit_data": assets.PipelineConfig(mode="restricted"),
        "pdfs": assets.PipelineConfig(mode="restricted"),
        "research_cards": assets.PipelineConfig(mode="restricted"),
        "knowledge_graph": assets.PipelineConfig(mode="restricted"),
        "vector_store": assets.PipelineConfig(mode="restricted"),
    }
)

full_config = RunConfig(
    ops={
        "rit_data": assets.PipelineConfig(mode="full"),
        "pdfs": assets.PipelineConfig(mode="full"),
        "research_cards": assets.PipelineConfig(mode="full"),
        "knowledge_graph": assets.PipelineConfig(mode="full"),
        "vector_store": assets.PipelineConfig(mode="full"),
    }
)

# Define Jobs
restricted_job = define_asset_job(
    name="restricted_pipeline",
    selection="*",
    config=restricted_config,
    description="Run the pipeline on a small subset of data (Fast)."
)

full_job = define_asset_job(
    name="full_pipeline",
    selection="*",
    config=full_config,
    description="Run the pipeline on ALL data (Slow, comprehensive)."
)

defs = Definitions(
    assets=all_assets,
    jobs=[restricted_job, full_job]
)
