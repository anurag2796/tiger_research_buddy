# 🐅 TigerBrain: Complete System Documentation

**Version:** 2.0.0 (TigerStack)  
**Last Updated:** February 9, 2026  
**Status:** Production-Ready  

---

## 📋 Documentation Index

This is the master documentation hub for the TigerBrain system. The documentation is organized into focused modules for deep technical understanding.

### 🏗️ Core Documentation

| Document | Description | Lines | Audience |
|----------|-------------|-------|----------|
| **[01 - Architecture](./01_architecture.md)** | Complete system architecture, design decisions, and technology stack | ~1200 | Architects, Senior Devs |
| **[02 - Code Reference](./02_code_reference.md)** | Module-by-module code walkthrough with examples | ~1500 | Developers |
| **[03 - API Reference](./03_api_reference.md)** | Complete API documentation for all public interfaces | ~800 | Integration Developers |
| **[04 - Configuration](./04_configuration.md)** | All configuration parameters, environment variables, and tuning | ~600 | DevOps, System Admins |
| **[05 - Data Pipeline](./05_data_pipeline.md)** | Deep dive into crawling, distillation, and graph construction | ~900 | Data Engineers |
| **[06 - Deployment](./06_deployment.md)** | Production deployment guide with Docker, monitoring, scaling | ~700 | DevOps Engineers |
| **[07 - Troubleshooting](./07_troubleshooting.md)** | Common issues, debugging techniques, performance optimization | ~500 | Support, Developers |
| **[08 - Challenges](./08_current_challenges.md)** | Current technical limitations and known issues | ~400 | Architects, Developers |

### 📊 Total Documentation: ~6,200 lines

---

## 🎯 Quick Navigation

### For New Developers
1. Start with [Architecture](./01_architecture.md) to understand the system
2. Read [Code Reference](./02_code_reference.md) for implementation details
3. Set up using [Deployment](./06_deployment.md)

### For System Administrators
1. Review [Configuration](./04_configuration.md) for tuning parameters
2. Implement [Deployment](./06_deployment.md) procedures
3. Setup monitoring from [Troubleshooting](./07_troubleshooting.md)

### For Integration Partners
1. Read [API Reference](./03_api_reference.md)
2. Review [Configuration](./04_configuration.md) for endpoints
3. Check [Troubleshooting](./07_troubleshooting.md) for common integration issues

---

## 🔑 Key Concepts

### The TigerStack
TigerBrain uses a hybrid RAG architecture combining:
- **Knowledge Graph** (NetworkX) - Structured relationships
- **Vector Store** (ChromaDB/LanceDB) - Semantic search
- **Local LLM** (Ollama) - Privacy-preserving inference

### Core Workflows
1. **Data Ingestion** → SmartCrawler → DeepDistiller → Graph Builder
2. **Query Processing** → Intent Classifier → Hybrid Retriever → Response Synthesizer
3. **Autonomous Maintenance** → Auditor → Patcher → Graph Updater (Phase 5)

---

## 📖 Document Summaries

### 01 - Architecture
Comprehensive overview of system design including:
- High-level architecture diagrams
- Technology selection rationale (why NetworkX over Neo4j, why ChromaDB, etc.)
- Data flow diagrams
- Component interaction patterns
- Design patterns and principles

**Key Topics:**
- The "TigerStack" philosophy
- Hybrid RAG architecture
- Local-first AI design
- Scalability considerations

### 02 - Code Reference
Complete walkthrough of every major module with:
- File-by-file code explanations
- Function signatures and purposes
- Usage examples
- Internal algorithms
- Dependencies and imports

**Key Modules:**
- `src/crawlers/` - Web scraping agents
- `src/knowledge_graph/` - Graph construction
- `src/retrieval/` - Query processing
- `src/generation/` - Response synthesis
- `src/ui/` - Streamlit interface

### 03 - API Reference
Formal API documentation including:
- All public classes and methods
- Parameter specifications
- Return types
- Error handling
- Usage examples

**APIs Covered:**
- VectorStore API
- HybridRetriever API
- GraphBuilder API
- OllamaClient API
- ResponseSynthesizer API

### 04 - Configuration
Exhaustive configuration reference:
- Environment variables
- Config file format
- Tuning parameters
- Performance settings
- Security configurations

**Configuration Files:**
- `src/utils/config.py`
- `.env` template
- Ollama Modelfile
- Prompt templates

### 05 - Data Pipeline
Deep technical dive into data engineering:
- SmartCrawler implementation
- DeepDistiller PDF processing
- Entity resolution algorithms
- Graph construction logic
- Quality assurance

**Pipeline Stages:**
1. Web Crawling
2. PDF Distillation
3. Entity Extraction
4. Graph Assembly
5. Vector Indexing

### 06 - Deployment
Production deployment procedures:
- Docker containerization
- Environment setup
- Ollama configuration
- Monitoring and logging
- Backup procedures
- Scaling strategies

**Deployment Targets:**
- Local development
- Single-server production
- Multi-container setup
- Cloud deployment (AWS/GCP/Azure)

### 07 - Troubleshooting
Comprehensive problem-solving guide:
- Common errors and solutions
- Performance optimization
- Debugging techniques
- Log analysis
- Recovery procedures

**Issue Categories:**
- Installation problems
- Runtime errors
- Performance issues
- Data quality problems
- Integration failures

---

## 🚀 Quick Start Guide

```bash
# 1. Clone and setup
git clone <repo>
cd tiger_research_buddy
pip install -r requirements.txt

# 2. Configure
cp .env.template .env
# Edit .env with your settings

# 3. Initialize data
python scripts/setup_v2.py

# 4. Run
streamlit run src/ui/app.py
```

For detailed setup, see [Deployment Guide](./06_deployment.md).

---

## 📚 Additional Resources

- **Project README**: `/README.md` - High-level project overview
- **Technical Reports**: `/docs/technical_report_experiment_4.md`
- **Migration Guide**: `/docs/migration_reasons.txt`
- **Future Roadmap**: `/docs/future_roadmap_ideas.md`
- **Implementation Plans**: `/docs/final_implementation_plan.md`

---

## 🤝 Contributing

When contributing to TigerBrain:
1. Read relevant wiki sections first
2. Follow code patterns documented in [Code Reference](./02_code_reference.md)
3. Update wiki docs when adding features
4. Add tests as documented in [Troubleshooting](./07_troubleshooting.md)

---

## 📧 Support

For questions about this documentation:
- File an issue with the `documentation` label
- Reference specific wiki page and section
- Include your use case context

---

**Built with ❤️ at RIT** 🐅

*Last generated: February 9, 2026*
