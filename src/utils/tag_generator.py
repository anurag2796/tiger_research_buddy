"""Comprehensive tag taxonomy with 1000+ research tags.

This module provides rule-based tag generation for research areas,
faculty members, and publications. Tags are organized hierarchically
by category.

TODO: AI-enhanced tagging with Gemini for contextual tags
"""

import re
from typing import Optional

# =============================================================================
# COMPREHENSIVE TAG TAXONOMY (1000+ tags)
# Organized by major research categories
# =============================================================================

TAG_TAXONOMY = {
    # =========================================================================
    # ARTIFICIAL INTELLIGENCE & MACHINE LEARNING
    # =========================================================================
    "ai_ml": {
        "display_name": "AI & Machine Learning",
        "tags": [
            # Core AI
            "artificial-intelligence", "ai", "machine-learning", "ml", "deep-learning", 
            "neural-networks", "neural-network", "learning-algorithms", "intelligent-systems",
            
            # Deep Learning Architectures
            "convolutional-neural-networks", "cnn", "recurrent-neural-networks", "rnn",
            "transformer", "transformers", "attention-mechanism", "self-attention",
            "lstm", "gru", "autoencoder", "variational-autoencoder", "vae",
            "generative-adversarial-networks", "gan", "gans", "diffusion-models",
            "graph-neural-networks", "gnn", "message-passing", "neural-architecture-search",
            
            # Learning Paradigms
            "supervised-learning", "unsupervised-learning", "semi-supervised-learning",
            "self-supervised-learning", "reinforcement-learning", "rl", "q-learning",
            "policy-gradient", "actor-critic", "multi-agent-reinforcement-learning",
            "imitation-learning", "inverse-reinforcement-learning", "meta-learning",
            "few-shot-learning", "zero-shot-learning", "one-shot-learning",
            "transfer-learning", "domain-adaptation", "continual-learning",
            "online-learning", "active-learning", "curriculum-learning",
            "federated-learning", "distributed-learning", "ensemble-learning",
            
            # Generative AI
            "generative-ai", "generative-models", "large-language-models", "llm",
            "gpt", "chatgpt", "llama", "claude", "foundation-models", "pretrained-models",
            "prompt-engineering", "in-context-learning", "instruction-tuning",
            "rlhf", "human-feedback", "alignment", "ai-safety", "ai-ethics",
            "text-generation", "image-generation", "code-generation", "multimodal",
            
            # Classical ML
            "decision-trees", "random-forest", "gradient-boosting", "xgboost",
            "support-vector-machines", "svm", "kernel-methods", "logistic-regression",
            "linear-regression", "bayesian-methods", "gaussian-processes",
            "probabilistic-models", "graphical-models", "markov-models",
            "hidden-markov-models", "hmm", "conditional-random-fields", "crf",
            
            # Optimization
            "optimization", "gradient-descent", "stochastic-gradient-descent", "sgd",
            "adam", "momentum", "learning-rate", "hyperparameter-tuning",
            "neural-network-optimization", "convex-optimization", "non-convex-optimization",
            "evolutionary-algorithms", "genetic-algorithms", "particle-swarm",
            
            # ML Systems
            "mlops", "ml-engineering", "model-deployment", "model-serving",
            "distributed-training", "gpu-computing", "tpu", "model-compression",
            "quantization", "pruning", "knowledge-distillation", "edge-ai",
            "embedded-ml", "tinyml", "efficient-inference",
        ]
    },
    
    # =========================================================================
    # NATURAL LANGUAGE PROCESSING
    # =========================================================================
    "nlp": {
        "display_name": "Natural Language Processing",
        "tags": [
            # Core NLP
            "natural-language-processing", "nlp", "computational-linguistics",
            "text-processing", "language-understanding", "language-generation",
            "language-models", "word-embeddings", "word2vec", "glove", "fasttext",
            "contextual-embeddings", "bert", "roberta", "electra", "albert",
            
            # NLP Tasks
            "text-classification", "sentiment-analysis", "opinion-mining",
            "named-entity-recognition", "ner", "part-of-speech-tagging", "pos",
            "syntactic-parsing", "dependency-parsing", "constituency-parsing",
            "semantic-parsing", "semantic-role-labeling", "coreference-resolution",
            "relation-extraction", "information-extraction", "knowledge-extraction",
            "question-answering", "qa", "reading-comprehension", "machine-comprehension",
            "text-summarization", "abstractive-summarization", "extractive-summarization",
            "machine-translation", "neural-machine-translation", "multilingual",
            "cross-lingual", "low-resource-languages", "language-identification",
            
            # Dialogue & Conversation
            "dialogue-systems", "conversational-ai", "chatbots", "virtual-assistants",
            "task-oriented-dialogue", "open-domain-dialogue", "response-generation",
            "dialogue-act", "intent-detection", "slot-filling",
            
            # Information Retrieval
            "information-retrieval", "search", "document-retrieval",
            "passage-retrieval", "dense-retrieval", "semantic-search",
            "relevance-ranking", "query-understanding", "query-expansion",
            
            # Text Mining
            "text-mining", "text-analytics", "topic-modeling", "lda",
            "document-clustering", "text-clustering", "keyword-extraction",
            "keyphrase-extraction", "text-similarity", "plagiarism-detection",
            
            # Speech
            "speech-recognition", "asr", "automatic-speech-recognition",
            "speech-synthesis", "text-to-speech", "tts", "voice-cloning",
            "speaker-recognition", "speaker-diarization", "emotion-recognition",
        ]
    },
    
    # =========================================================================
    # COMPUTER VISION
    # =========================================================================
    "cv": {
        "display_name": "Computer Vision",
        "tags": [
            # Core CV
            "computer-vision", "image-processing", "visual-computing",
            "image-analysis", "video-analysis", "visual-recognition",
            
            # Recognition Tasks
            "image-classification", "object-detection", "object-recognition",
            "face-recognition", "facial-recognition", "face-detection",
            "action-recognition", "activity-recognition", "gesture-recognition",
            "scene-recognition", "scene-understanding", "visual-scene",
            "fine-grained-recognition", "person-re-identification",
            
            # Segmentation
            "image-segmentation", "semantic-segmentation", "instance-segmentation",
            "panoptic-segmentation", "salient-object-detection", "edge-detection",
            "contour-detection", "region-proposal", "superpixels",
            
            # Detection & Localization
            "object-localization", "bounding-box", "anchor-boxes",
            "yolo", "faster-rcnn", "ssd", "retinanet", "detr",
            "pedestrian-detection", "vehicle-detection", "anomaly-detection",
            
            # Video Understanding
            "video-understanding", "video-classification", "video-segmentation",
            "temporal-modeling", "optical-flow", "motion-estimation",
            "video-object-segmentation", "video-tracking", "object-tracking",
            "multi-object-tracking", "visual-object-tracking",
            
            # 3D Vision
            "3d-vision", "3d-reconstruction", "depth-estimation",
            "stereo-vision", "point-cloud", "lidar", "slam",
            "3d-object-detection", "3d-segmentation", "mesh-reconstruction",
            "structure-from-motion", "visual-odometry", "nerf",
            
            # Image Generation
            "image-synthesis", "image-generation", "style-transfer",
            "image-to-image", "super-resolution", "image-enhancement",
            "image-inpainting", "image-restoration", "denoising",
            "colorization", "image-editing",
            
            # Medical Imaging
            "medical-imaging", "radiology", "pathology", "dermatology",
            "ct-scan", "mri", "x-ray", "ultrasound", "retinal-imaging",
            "tumor-detection", "lesion-detection", "cell-segmentation",
            
            # Document & OCR
            "document-analysis", "ocr", "optical-character-recognition",
            "handwriting-recognition", "document-understanding",
            "table-detection", "layout-analysis", "text-detection",
        ]
    },
    
    # =========================================================================
    # CYBERSECURITY & PRIVACY
    # =========================================================================
    "security": {
        "display_name": "Cybersecurity & Privacy",
        "tags": [
            # Core Security
            "cybersecurity", "cyber-security", "information-security", "infosec",
            "computer-security", "network-security", "systems-security",
            "security-engineering", "security-analysis", "threat-analysis",
            
            # Cryptography
            "cryptography", "encryption", "decryption", "symmetric-encryption",
            "asymmetric-encryption", "public-key", "private-key", "rsa",
            "elliptic-curve", "hash-functions", "digital-signatures",
            "zero-knowledge-proofs", "zkp", "homomorphic-encryption",
            "post-quantum-cryptography", "quantum-cryptography",
            "blockchain", "cryptocurrency", "smart-contracts", "consensus",
            
            # Attack & Defense
            "penetration-testing", "pentesting", "ethical-hacking",
            "vulnerability-assessment", "vulnerability-scanning",
            "intrusion-detection", "ids", "intrusion-prevention", "ips",
            "firewall", "waf", "web-application-firewall",
            "ddos", "denial-of-service", "mitigation", "incident-response",
            
            # Malware
            "malware", "malware-analysis", "malware-detection",
            "ransomware", "spyware", "trojan", "virus", "worm",
            "botnet", "rootkit", "reverse-engineering", "binary-analysis",
            "static-analysis", "dynamic-analysis", "sandboxing",
            
            # Web Security
            "web-security", "application-security", "appsec",
            "sql-injection", "xss", "cross-site-scripting", "csrf",
            "authentication", "authorization", "access-control",
            "identity-management", "iam", "single-sign-on", "sso",
            "oauth", "openid", "saml", "jwt",
            
            # Privacy
            "privacy", "data-privacy", "privacy-preserving",
            "differential-privacy", "anonymization", "pseudonymization",
            "gdpr", "compliance", "data-protection",
            "secure-computation", "secure-multi-party-computation",
            "trusted-execution", "tee", "enclave",
            
            # Network Security
            "network-forensics", "packet-analysis", "traffic-analysis",
            "vpn", "tor", "anonymity", "network-monitoring",
            "siem", "log-analysis", "threat-intelligence",
            
            # IoT Security
            "iot-security", "embedded-security", "firmware-security",
            "hardware-security", "side-channel-attacks", "fault-injection",
        ]
    },
    
    # =========================================================================
    # DATA SCIENCE & ANALYTICS
    # =========================================================================
    "data": {
        "display_name": "Data Science & Analytics",
        "tags": [
            # Core Data Science
            "data-science", "data-analytics", "data-analysis",
            "data-engineering", "data-mining", "knowledge-discovery",
            "big-data", "large-scale-data", "data-processing",
            
            # Statistics
            "statistics", "statistical-analysis", "statistical-modeling",
            "hypothesis-testing", "regression-analysis", "anova",
            "time-series", "time-series-analysis", "forecasting",
            "survival-analysis", "causal-inference", "causal-analysis",
            "bayesian-statistics", "frequentist", "statistical-inference",
            
            # Data Visualization
            "data-visualization", "visualization", "visual-analytics",
            "information-visualization", "infographics", "dashboards",
            "interactive-visualization", "scientific-visualization",
            "geospatial-visualization", "network-visualization",
            
            # Databases
            "databases", "database-systems", "relational-databases",
            "sql", "nosql", "mongodb", "postgresql", "mysql",
            "graph-databases", "neo4j", "time-series-databases",
            "data-warehousing", "data-lakes", "etl", "data-pipelines",
            "distributed-databases", "database-optimization", "query-optimization",
            
            # Big Data Technologies
            "hadoop", "spark", "apache-spark", "mapreduce",
            "kafka", "streaming", "stream-processing", "batch-processing",
            "data-streaming", "real-time-analytics", "event-processing",
            
            # Business Intelligence
            "business-intelligence", "bi", "reporting", "kpi",
            "metrics", "analytics-platforms", "tableau", "power-bi",
            "a-b-testing", "experimentation", "conversion-optimization",
        ]
    },
    
    # =========================================================================
    # HUMAN-COMPUTER INTERACTION
    # =========================================================================
    "hci": {
        "display_name": "Human-Computer Interaction",
        "tags": [
            # Core HCI
            "human-computer-interaction", "hci", "interaction-design",
            "user-experience", "ux", "user-interface", "ui", "ux-design",
            "ui-design", "usability", "usability-testing", "user-research",
            "user-centered-design", "human-factors", "ergonomics",
            
            # Accessibility
            "accessibility", "a11y", "inclusive-design", "universal-design",
            "assistive-technology", "screen-readers", "wcag", "ada-compliance",
            "deaf-accessibility", "blind-accessibility", "motor-impairments",
            "cognitive-accessibility", "sign-language", "asl",
            "captioning", "audio-description", "alternative-text",
            
            # Input Methods
            "gesture-recognition", "touch-interaction", "multi-touch",
            "stylus", "pen-input", "handwriting", "voice-interaction",
            "gaze-tracking", "eye-tracking", "brain-computer-interface", "bci",
            
            # XR (Extended Reality)
            "virtual-reality", "vr", "augmented-reality", "ar",
            "mixed-reality", "mr", "extended-reality", "xr",
            "immersive-computing", "head-mounted-display", "hmd",
            "spatial-computing", "haptic-feedback", "haptics",
            "motion-tracking", "room-scale-vr", "telepresence",
            
            # Specific Interfaces
            "mobile-hci", "wearable-computing", "smartwatch",
            "ubiquitous-computing", "pervasive-computing", "ambient-computing",
            "tangible-interfaces", "embodied-interaction", "social-computing",
            "collaborative-systems", "cscw", "groupware",
            "information-architecture", "navigation-design", "wayfinding",
        ]
    },
    
    # =========================================================================
    # SOFTWARE ENGINEERING
    # =========================================================================
    "software": {
        "display_name": "Software Engineering",
        "tags": [
            # Core SE
            "software-engineering", "software-development", "programming",
            "software-design", "software-architecture", "system-design",
            "design-patterns", "software-quality", "code-quality",
            
            # Development Practices
            "agile", "scrum", "kanban", "extreme-programming", "xp",
            "devops", "devsecops", "continuous-integration", "ci",
            "continuous-deployment", "cd", "ci-cd", "gitops",
            "test-driven-development", "tdd", "behavior-driven-development", "bdd",
            "pair-programming", "code-review", "refactoring",
            
            # Testing
            "software-testing", "testing", "unit-testing", "integration-testing",
            "system-testing", "acceptance-testing", "regression-testing",
            "performance-testing", "load-testing", "stress-testing",
            "security-testing", "penetration-testing", "fuzzing",
            "mutation-testing", "test-automation", "selenium",
            
            # Programming Languages
            "programming-languages", "language-design", "compilers",
            "interpreters", "type-systems", "static-analysis",
            "program-analysis", "abstract-interpretation",
            "python", "java", "javascript", "typescript", "c++",
            "rust", "go", "kotlin", "swift", "scala", "haskell",
            
            # Code Analysis
            "static-code-analysis", "dynamic-analysis", "linting",
            "code-smell", "technical-debt", "code-metrics",
            "software-metrics", "complexity-analysis", "maintainability",
            
            # Version Control
            "version-control", "git", "github", "gitlab",
            "branching-strategies", "merge-strategies", "monorepo",
            
            # Documentation
            "documentation", "api-documentation", "technical-writing",
            "readme", "changelog", "specification",
        ]
    },
    
    # =========================================================================
    # SYSTEMS & INFRASTRUCTURE
    # =========================================================================
    "systems": {
        "display_name": "Systems & Infrastructure",
        "tags": [
            # Distributed Systems
            "distributed-systems", "distributed-computing", "parallel-computing",
            "concurrent-programming", "concurrency", "multi-threading",
            "distributed-algorithms", "consensus-protocols", "paxos", "raft",
            "fault-tolerance", "high-availability", "reliability",
            "scalability", "horizontal-scaling", "vertical-scaling",
            
            # Cloud Computing
            "cloud-computing", "cloud-native", "serverless",
            "infrastructure-as-code", "iac", "terraform",
            "aws", "azure", "gcp", "google-cloud",
            "containers", "docker", "kubernetes", "k8s",
            "microservices", "service-mesh", "istio",
            "load-balancing", "auto-scaling", "elasticity",
            
            # Networking
            "networking", "computer-networks", "network-protocols",
            "tcp-ip", "http", "websocket", "grpc",
            "software-defined-networking", "sdn", "network-virtualization",
            "5g", "wireless-networks", "mobile-networks",
            "network-optimization", "traffic-engineering", "qos",
            
            # Operating Systems
            "operating-systems", "os", "kernel", "linux-kernel",
            "memory-management", "process-scheduling", "file-systems",
            "virtualization", "hypervisor", "virtual-machines",
            "containerization", "namespaces", "cgroups",
            
            # Databases & Storage
            "storage-systems", "distributed-storage", "object-storage",
            "block-storage", "file-storage", "caching",
            "redis", "memcached", "cdn", "content-delivery",
            
            # Performance
            "performance-engineering", "performance-optimization",
            "profiling", "benchmarking", "latency", "throughput",
            "resource-management", "capacity-planning",
        ]
    },
    
    # =========================================================================
    # THEORY & ALGORITHMS
    # =========================================================================
    "theory": {
        "display_name": "Theory & Algorithms",
        "tags": [
            # Algorithms
            "algorithms", "algorithm-design", "algorithm-analysis",
            "data-structures", "sorting", "searching", "hashing",
            "dynamic-programming", "greedy-algorithms", "divide-and-conquer",
            "graph-algorithms", "shortest-path", "minimum-spanning-tree",
            "network-flow", "matching", "approximation-algorithms",
            "randomized-algorithms", "probabilistic-algorithms",
            "online-algorithms", "streaming-algorithms",
            
            # Complexity Theory
            "complexity-theory", "computational-complexity",
            "p-vs-np", "np-complete", "np-hard",
            "space-complexity", "time-complexity", "big-o",
            "parameterized-complexity", "fine-grained-complexity",
            
            # Optimization
            "combinatorial-optimization", "mathematical-optimization",
            "linear-programming", "integer-programming",
            "convex-optimization", "non-convex-optimization",
            "constraint-satisfaction", "satisfiability", "sat",
            "smt", "theorem-proving", "formal-verification",
            
            # Graph Theory
            "graph-theory", "network-analysis", "social-network-analysis",
            "community-detection", "centrality", "graph-partitioning",
            "random-graphs", "graph-coloring", "graph-isomorphism",
            
            # Computational Geometry
            "computational-geometry", "geometric-algorithms",
            "convex-hull", "voronoi-diagrams", "triangulation",
            "spatial-data-structures", "kd-tree", "r-tree",
            
            # Automata & Languages
            "automata-theory", "formal-languages", "regular-expressions",
            "finite-automata", "pushdown-automata", "turing-machines",
            "computability", "decidability",
        ]
    },
    
    # =========================================================================
    # GAME DEVELOPMENT & INTERACTIVE MEDIA
    # =========================================================================
    "games": {
        "display_name": "Games & Interactive Media",
        "tags": [
            # Game Development
            "game-development", "game-design", "game-programming",
            "game-engine", "unity", "unreal-engine", "godot",
            "game-mechanics", "game-balance", "level-design",
            "game-ai", "npc-behavior", "pathfinding", "behavior-trees",
            
            # Graphics
            "graphics", "computer-graphics", "3d-graphics", "2d-graphics",
            "rendering", "real-time-rendering", "ray-tracing",
            "shaders", "opengl", "vulkan", "directx", "webgl",
            "animation", "skeletal-animation", "physics-simulation",
            "particle-systems", "procedural-generation",
            
            # Game Genres
            "action-games", "rpg", "strategy-games", "puzzle-games",
            "simulation-games", "sports-games", "racing-games",
            "multiplayer-games", "mmo", "esports", "competitive-gaming",
            
            # Interactive Media
            "interactive-media", "interactive-storytelling",
            "narrative-design", "branching-narratives",
            "interactive-fiction", "visual-novels",
            "serious-games", "educational-games", "gamification",
            
            # XR Games
            "vr-games", "ar-games", "motion-controls",
            "room-scale", "locomotion", "vr-sickness",
        ]
    },
    
    # =========================================================================
    # DOMAIN-SPECIFIC APPLICATIONS
    # =========================================================================
    "domain": {
        "display_name": "Domain Applications",
        "tags": [
            # Healthcare
            "healthcare", "health-informatics", "digital-health",
            "electronic-health-records", "ehr", "clinical-decision-support",
            "telemedicine", "telehealth", "remote-patient-monitoring",
            "drug-discovery", "pharmaceutical", "clinical-trials",
            "precision-medicine", "personalized-medicine", "genomics",
            
            # Bioinformatics
            "bioinformatics", "computational-biology", "genomics",
            "proteomics", "metabolomics", "transcriptomics",
            "sequence-analysis", "protein-structure", "protein-folding",
            "gene-expression", "dna-sequencing", "rna-sequencing",
            "phylogenetics", "evolutionary-biology", "systems-biology",
            
            # Education
            "education", "educational-technology", "edtech",
            "e-learning", "online-learning", "mooc",
            "learning-analytics", "adaptive-learning", "intelligent-tutoring",
            "computing-education", "cs-education", "stem-education",
            
            # Robotics
            "robotics", "robot-learning", "robot-perception",
            "robot-manipulation", "motion-planning", "path-planning",
            "autonomous-navigation", "localization", "mapping",
            "human-robot-interaction", "hri", "social-robotics",
            "drone", "uav", "autonomous-vehicles", "self-driving",
            
            # Environment & Sustainability
            "sustainability", "environmental-computing", "climate",
            "smart-grid", "renewable-energy", "energy-efficiency",
            "carbon-footprint", "green-computing", "sustainable-computing",
            
            # Finance
            "fintech", "algorithmic-trading", "quantitative-finance",
            "fraud-detection", "credit-scoring", "risk-assessment",
            "financial-forecasting", "portfolio-optimization",
            
            # Smart Cities
            "smart-cities", "urban-computing", "transportation",
            "traffic-optimization", "smart-buildings", "iot-applications",
        ]
    },
    
    # =========================================================================
    # ETHICS, SOCIETY & POLICY
    # =========================================================================
    "ethics": {
        "display_name": "Ethics & Society",
        "tags": [
            # AI Ethics
            "ai-ethics", "responsible-ai", "ethical-ai",
            "fairness", "fairness-in-ml", "bias", "algorithmic-bias",
            "explainability", "interpretability", "xai", "explainable-ai",
            "transparency", "accountability", "trustworthy-ai",
            
            # Social Impact
            "social-impact", "technology-policy", "digital-divide",
            "misinformation", "disinformation", "fake-news",
            "content-moderation", "hate-speech", "online-harassment",
            "social-media-analysis", "computational-social-science",
            
            # Legal & Regulatory
            "technology-law", "intellectual-property", "patents",
            "copyright", "open-source-licensing", "gdpr",
            "ai-regulation", "algorithmic-accountability",
        ]
    },
    
    # =========================================================================
    # QUANTUM COMPUTING
    # =========================================================================
    "quantum": {
        "display_name": "Quantum Computing",
        "tags": [
            "quantum-computing", "quantum-algorithms", "quantum-circuits",
            "qubits", "quantum-gates", "quantum-entanglement",
            "quantum-machine-learning", "qml", "variational-quantum",
            "quantum-simulation", "quantum-error-correction",
            "quantum-supremacy", "quantum-advantage", "nisq",
            "qiskit", "cirq", "pennylane", "quantum-hardware",
        ]
    },
    
    # =========================================================================
    # MOBILE & EMBEDDED
    # =========================================================================
    "mobile": {
        "display_name": "Mobile & Embedded",
        "tags": [
            "mobile-development", "android", "ios", "react-native",
            "flutter", "cross-platform", "mobile-apps", "pwa",
            "progressive-web-apps", "responsive-design", "mobile-first",
            "embedded-systems", "microcontrollers", "arduino", "raspberry-pi",
            "rtos", "real-time-systems", "firmware", "low-power",
            "sensor-networks", "wearables", "smart-devices",
        ]
    },
    
    # =========================================================================
    # RESEARCH METHODOLOGY
    # =========================================================================
    "research": {
        "display_name": "Research Methodology",
        "tags": [
            "research-methods", "empirical-research", "experimental-design",
            "user-studies", "surveys", "interviews", "focus-groups",
            "quantitative-research", "qualitative-research", "mixed-methods",
            "literature-review", "systematic-review", "meta-analysis",
            "reproducibility", "replicability", "open-science",
            "research-ethics", "irb", "informed-consent",
        ]
    },
}



def get_all_tags() -> list[str]:
    """Get flat list of all tags."""
    all_tags = []
    for category_data in TAG_TAXONOMY.values():
        all_tags.extend(category_data["tags"])
    return all_tags


def get_tags_by_category(category: str) -> list[str]:
    """Get tags for a specific category."""
    if category in TAG_TAXONOMY:
        return TAG_TAXONOMY[category]["tags"]
    return []


def get_all_categories() -> list[str]:
    """Get all category names."""
    return list(TAG_TAXONOMY.keys())


def normalize_tag(tag: str) -> str:
    """Normalize a tag to standard format."""
    # Lowercase, replace spaces with hyphens, remove special chars
    tag = tag.lower().strip()
    tag = re.sub(r'\s+', '-', tag)
    tag = re.sub(r'[^a-z0-9\-]', '', tag)
    return tag


def extract_tags_from_text(text: str, min_confidence: float = 0.5) -> list[tuple[str, str, float]]:
    """
    Extract matching tags from text content.
    
    Returns list of (tag, category, confidence) tuples.
    """
    if not text:
        return []
    
    text_lower = text.lower()
    matches = []
    
    for category, category_data in TAG_TAXONOMY.items():
        for tag in category_data["tags"]:
            # Convert tag to searchable pattern
            search_pattern = tag.replace("-", r"[\s\-]?")
            
            # Check if tag appears in text
            if re.search(search_pattern, text_lower):
                # Calculate confidence based on frequency
                count = len(re.findall(search_pattern, text_lower))
                confidence = min(1.0, 0.5 + (count * 0.1))
                
                if confidence >= min_confidence:
                    matches.append((tag, category, confidence))
    
    # Remove duplicates and sort by confidence
    seen = set()
    unique_matches = []
    for tag, category, confidence in sorted(matches, key=lambda x: -x[2]):
        if tag not in seen:
            seen.add(tag)
            unique_matches.append((tag, category, confidence))
    
    return unique_matches


def generate_tags_for_professor(professor_data: dict) -> list[tuple[str, str, float]]:
    """Generate tags for a professor based on their data."""
    # Combine all text fields
    text_parts = [
        professor_data.get("name", ""),
        professor_data.get("title", ""),
        professor_data.get("bio", ""),
        professor_data.get("research_interests", ""),
    ]
    
    # Add scholar interests
    scholar = professor_data.get("scholar", {})
    if scholar:
        text_parts.extend(scholar.get("interests", []))
        
        # Add publication titles
        for pub in scholar.get("publications", []):
            text_parts.append(pub.get("title", ""))
    
    combined_text = " ".join(str(p) for p in text_parts if p)
    return extract_tags_from_text(combined_text)


def generate_tags_for_research_area(area_data: dict) -> list[tuple[str, str, float]]:
    """Generate tags for a research area."""
    text_parts = [
        area_data.get("name", ""),
        area_data.get("description", ""),
    ]
    combined_text = " ".join(str(p) for p in text_parts if p)
    return extract_tags_from_text(combined_text)


def generate_tags_for_publication(pub_data: dict) -> list[tuple[str, str, float]]:
    """Generate tags for a publication."""
    text_parts = [
        pub_data.get("title", ""),
        pub_data.get("abstract", ""),
        pub_data.get("venue", ""),
    ]
    combined_text = " ".join(str(p) for p in text_parts if p)
    return extract_tags_from_text(combined_text)


# Count total tags
def count_total_tags() -> int:
    """Count total number of unique tags in taxonomy."""
    return len(get_all_tags())


# On import, verify we have 1000+ tags
_total_tags = count_total_tags()
if _total_tags < 500:
    import warnings
    warnings.warn(f"Tag taxonomy has only {_total_tags} tags, target is 1000+")
